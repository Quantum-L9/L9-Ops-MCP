# --- L9_META ---
# l9_schema: 1
# artifact_type: test
# tags: [ci-proof, repository-structure, wiring]
# retrieval: on_demand
# status: active
# --- /L9_META ---

"""Structural wiring regressions; synthetic fixtures never repair real content gaps."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.impact_analysis import analyze, build_reverse, load_manifest, resolve_file_to_id
from scripts.repo_structure import ROOT, StructureError, load_repository
from scripts.validate_wiring import validate_repository


def put(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_index(root: Path) -> None:
    files = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "AGENT_RETRIEVAL_INDEX.yaml":
            continue
        rel = path.relative_to(root).as_posix()
        files[rel] = {
            "tags": ["kernels"] if rel.startswith("docs/kernels/") else ["general"],
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    put(root, "AGENT_RETRIEVAL_INDEX.yaml", yaml.safe_dump({"files": files}))


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    for kid, requires in (("alpha_kernel.v1", []), ("beta_kernel.v1", ["alpha_kernel.v1"])):
        put(
            root,
            f"docs/kernels/R5/{kid}.yaml",
            yaml.safe_dump(
                {
                    "kernel_id": kid,
                    "version": "1.0.0",
                    "ring": "R5",
                    "category": "test",
                    "title": kid,
                    "purpose": "Structural regression test kernel",
                    "activation_phase": "on_demand",
                    "status": "active",
                    "overload_weight": 1,
                    "hard_bans": [],
                    "requires": requires,
                }
            ),
        )
    put(
        root,
        "schemas/kernel.canonical.schema.json",
        (ROOT / "schemas/kernel.canonical.schema.json").read_text(),
    )
    put(
        root,
        "skills/testing/check/SKILL.md",
        "---\nname: check\ndescription: Test structural wiring\nrequires: [alpha_kernel.v1]\n---\n# Check\n",
    )
    put(
        root,
        "playbooks/check/PLAYBOOK.md",
        "---\nname: check-playbook\nkernels_required: [beta_kernel.v1]\n"
        "skills_required: [check]\nsteps:\n  - file: steps/run.md\n---\n# Test playbook\n",
    )
    put(root, "playbooks/check/steps/run.md", "# Run\nExecute the structural check.\n")
    paths = [
        "docs/kernels/R5/alpha_kernel.v1.yaml",
        "docs/kernels/R5/beta_kernel.v1.yaml",
        "skills/testing/check/SKILL.md",
        "playbooks/check/PLAYBOOK.md",
    ]
    put(root, "AGENTS.md", "# Registry\n" + "\n".join(f"- [{p}]({p})" for p in paths) + "\n")
    put(root, "README.md", "# Commands\n```sh\nmake validate\n```\n")
    put(root, "Makefile", "include Repo.mk\nhelp:\n\t@echo help\n")
    put(root, "Repo.mk", "validate:\n\tpython3 scripts/proof.py\n")
    put(root, "scripts/proof.py", "import ast\nast.parse('x = 1')\n")
    put(
        root,
        ".github/workflows/proof.yaml",
        "name: proof\njobs:\n  check:\n    runs-on: ubuntu-latest\n"
        "    steps:\n      - run: python3 scripts/proof.py\n",
    )
    put(
        root,
        "pyproject.toml",
        '[project]\nname = "fixture"\nversion = "0.0.1"\n'
        '[project.scripts]\nfixture = "json:loads"\n',
    )
    for name in (
        "validate_helpers.py",
        "validate_command_parity.py",
        "validate_pyproject_entrypoints.py",
    ):
        shutil.copy2(ROOT / "scripts" / name, root / "scripts" / name)
    write_index(root)
    return root


def test_valid_consolidated_repo_checks_nonzero_actual_structure(repository: Path) -> None:
    repo = validate_repository(repository)
    assert not repo.failures
    assert len(repo.artifacts) == 4
    assert sum(f.status == "PASS" for f in repo.findings) > 15
    assert sum(map(len, repo.dependencies.values())) == 4
    assert any(f.check == "kernel-integrity" for f in repo.findings)
    assert any(f.check == "validate_pyproject_entrypoints.py" for f in repo.findings)
    assert any(f.check == "validate_command_parity.py" for f in repo.findings)


def test_real_repo_inventory_is_nonzero_and_does_not_hide_known_gaps() -> None:
    repo = load_repository(ROOT)
    assert len([a for a in repo.artifacts.values() if a.kind == "kernel"]) == 8
    assert len(repo.artifacts) >= 30
    assert sum(f.status == "PASS" for f in repo.findings) > 100
    assert repo.dependencies["l9_build_kernel.v1"] == {"l9_coding_kernel.v1"}
    # These are actual missing declarations, not doctrine/eval placeholders.
    assert any("developer_core_kernel.v1" in f.detail for f in repo.failures)
    assert any(
        f.status == "UNKNOWN" and "steps/step-00-intake.md" in f.detail for f in repo.findings
    )
    assert not any("microservice-build" in f.detail for f in repo.failures)
    assert any(f.status == "UNKNOWN" and f.check == "kernel-content-schema" for f in repo.findings)


@pytest.mark.parametrize("destination", ["docs/missing.md", "../outside.md", "/tmp/outside.md"])
def test_missing_agents_link_or_path_escape_fails(repository: Path, destination: str) -> None:
    with (repository / "AGENTS.md").open("a") as stream:
        stream.write(f"\n[bad]({destination})\n")
    with pytest.raises(StructureError):
        load_repository(repository)


def test_symlink_outside_repo_fails(repository: Path, tmp_path: Path) -> None:
    outside = put(tmp_path, "outside.md", "outside\n")
    (repository / "outside-link.md").symlink_to(outside)
    with (repository / "AGENTS.md").open("a") as stream:
        stream.write("\n[bad](outside-link.md)\n")
    with pytest.raises(StructureError, match="escapes"):
        load_repository(repository)


@pytest.mark.parametrize("values", [["missing_kernel.v1"], "alpha_kernel.v1", [3]])
def test_invalid_declared_dependencies_fail_closed(repository: Path, values: object) -> None:
    path = repository / "docs/kernels/R5/beta_kernel.v1.yaml"
    doc = yaml.safe_load(path.read_text())
    doc["requires"] = values
    path.write_text(yaml.safe_dump(doc))
    write_index(repository)
    repo = load_repository(repository)
    assert any(f.check == "dependency" for f in repo.failures)
    with pytest.raises(StructureError, match="invalid declared wiring"):
        load_manifest(repository)


def test_missing_declared_step_fails(repository: Path) -> None:
    (repository / "playbooks/check/steps/run.md").unlink()
    write_index(repository)
    repo = load_repository(repository)
    assert any(f.check == "declared-step" for f in repo.failures)


def test_declared_step_escape_fails(repository: Path) -> None:
    path = repository / "playbooks/check/PLAYBOOK.md"
    path.write_text(path.read_text().replace("steps/run.md", "../../../escape.md"))
    write_index(repository)
    repo = load_repository(repository)
    assert any("escapes repository" in f.detail for f in repo.failures)


@pytest.mark.parametrize(
    "text",
    [
        "{",
        "{}",
        "[]",
        '{"files": {"AGENTS.md": "old pack"}}',
        '{"kernels": {"registry": []}}',
        '{"kernels": {"registry": {}}}',
    ],
)
def test_malformed_unknown_empty_manifest_fails(repository: Path, text: str) -> None:
    put(repository, "MANIFEST.json", text)
    with pytest.raises(StructureError):
        load_repository(repository)


def test_empty_canonical_index_fails(repository: Path) -> None:
    put(repository, "AGENT_RETRIEVAL_INDEX.yaml", "files: {}\n")
    with pytest.raises(StructureError, match="nonempty"):
        load_repository(repository)


def test_missing_indexed_kernel_fails(repository: Path) -> None:
    (repository / "docs/kernels/R5/alpha_kernel.v1.yaml").unlink()
    with pytest.raises(StructureError):
        load_repository(repository)


def test_unindexed_canonical_kernel_fails(repository: Path) -> None:
    shutil.copy2(
        repository / "docs/kernels/R5/alpha_kernel.v1.yaml",
        repository / "docs/kernels/R5/unindexed.yaml",
    )
    with pytest.raises(StructureError, match="unindexed"):
        load_repository(repository)


def test_digest_mismatch_fails(repository: Path) -> None:
    path = repository / "docs/kernels/R5/alpha_kernel.v1.yaml"
    path.write_text(path.read_text() + "\n# drift\n")
    with pytest.raises(Exception, match="integrity failure"):
        load_repository(repository)


def test_actual_declared_transitive_impact_and_exact_changed_path(repository: Path) -> None:
    manifest = load_manifest(repository)
    result = analyze("alpha_kernel.v1", manifest, build_reverse(manifest))
    assert result["kernels"] == ["beta_kernel.v1"]
    assert result["skills"] == ["testing/check"]
    assert result["playbooks"] == ["check"]
    assert result["total"] == 3
    assert resolve_file_to_id("docs/kernels/R5/alpha_kernel.v1.yaml", manifest) == "alpha_kernel.v1"
    assert resolve_file_to_id("alpha_kernel.v1.yaml", manifest) is None
    with pytest.raises(StructureError, match="escapes"):
        resolve_file_to_id("../alpha_kernel.v1.yaml", manifest)


def test_legacy_registry_and_dependency_graph_remain_supported(repository: Path) -> None:
    put(
        repository,
        "MANIFEST.json",
        json.dumps(
            {
                "kernels": {
                    "registry": [
                        {"id": "alpha_kernel.v1", "file": "docs/kernels/R5/alpha_kernel.v1.yaml"}
                    ]
                },
                "skills": {"registry": [{"id": "check", "file": "skills/testing/check/SKILL.md"}]},
                "dependencyGraph": {"skillsRequiringKernels": {"check": ["alpha_kernel.v1"]}},
            }
        ),
    )
    manifest = load_manifest(repository)
    assert analyze("alpha_kernel.v1", manifest, build_reverse(manifest))["skills"] == ["check"]
    assert manifest["source"] == "legacy MANIFEST"


def test_invalid_legacy_dependency_source_fails(repository: Path) -> None:
    put(
        repository,
        "MANIFEST.json",
        json.dumps(
            {
                "kernels": {
                    "registry": [
                        {"id": "alpha_kernel.v1", "file": "docs/kernels/R5/alpha_kernel.v1.yaml"}
                    ]
                },
                "dependencyGraph": {
                    "skillsRequiringKernels": {"unknown-skill": ["alpha_kernel.v1"]}
                },
            }
        ),
    )
    with pytest.raises(StructureError, match="unknown skill source"):
        load_manifest(repository)


def test_make_include_and_yaml_workflow_missing_active_script_fails(repository: Path) -> None:
    put(repository, "Repo.mk", "validate:\n\tpython3 scripts/missing.py\n")
    repo = validate_repository(repository, run_validators=False)
    assert any("scripts/missing.py" in f.detail for f in repo.failures)
    put(
        repository,
        ".github/workflows/proof.yaml",
        "jobs:\n  proof:\n    steps:\n      - run: python3 scripts/also-missing.py\n",
    )
    repo = validate_repository(repository, run_validators=False)
    assert any("also-missing.py" in f.detail for f in repo.failures)


def test_optional_guarded_workflow_script_is_explicitly_not_applicable(repository: Path) -> None:
    put(
        repository,
        ".github/workflows/optional.yaml",
        "jobs:\n  check:\n    steps:\n"
        "      - run: |\n          if [ -f ci/upstream.py ]; then\n"
        "            python3 ci/upstream.py\n          else\n"
        "            echo optional upstream integration unavailable\n          fi\n",
    )
    repo = validate_repository(repository, run_validators=False)
    assert not repo.failures
    assert any(
        f.status == "NOT_APPLICABLE_WITH_REASON" and "ci/upstream.py" in f.detail
        for f in repo.findings
    )


@pytest.mark.parametrize(
    "script,args", [("validate_wiring.py", ["--all"]), ("impact_analysis.py", ["--all", "--json"])]
)
def test_clis_work_from_outside_cwd(
    repository: Path, tmp_path: Path, script: str, args: list[str]
) -> None:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), "--root", str(repository), *args],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    if script == "validate_wiring.py":
        assert "Artifacts checked: 4" in proc.stdout
    else:
        assert json.loads(proc.stdout)["artifacts_checked"] == 4


def test_unknown_selection_fails(repository: Path, tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/validate_wiring.py"),
            "--root",
            str(repository),
            "--id",
            "not-registered",
        ],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert proc.returncode == 1
    assert "empty or unknown" in proc.stderr


def test_optional_guard_does_not_hide_unguarded_same_script(repository: Path) -> None:
    put(
        repository,
        ".github/workflows/mixed.yaml",
        "jobs:\n  check:\n    steps:\n"
        "      - run: |\n          if [ -f ci/upstream.py ]; then\n"
        "            python3 ci/upstream.py\n          fi\n          python3 ci/upstream.py\n",
    )
    repo = validate_repository(repository, run_validators=False)
    assert any("ci/upstream.py" in finding.detail for finding in repo.failures)


def supersede_test_playbook(root: Path, target: str | None) -> None:
    # This is a synthetic fixture only. No real repository source is superseded.
    replacement = "" if target is None else f"superseded_by: {target}\n"
    put(
        root,
        "playbooks/old/PLAYBOOK.md",
        "---\nname: old\nstatus: superseded\n"
        + replacement
        + "kernel-requirements: [missing_kernel.v1]\nsteps:\n  - file: steps/missing.md\n---\n"
        "# Historical pipeline\nOriginal unavailable requirements remain declared.\n",
    )
    write_index(root)


def test_explicit_superseded_playbook_keeps_gaps_visible_and_validates_target(
    repository: Path,
) -> None:
    supersede_test_playbook(repository, "../check/PLAYBOOK.md")
    repo = load_repository(repository)
    assert not repo.failures
    assert repo.dependencies["old"] == set()
    assert any(f.status == "UNKNOWN" and "missing_kernel.v1" in f.detail for f in repo.findings)
    assert any(f.status == "UNKNOWN" and "steps/missing.md" in f.detail for f in repo.findings)
    assert any(
        f.status == "NOT_APPLICABLE_WITH_REASON" and f.check == "superseded-playbook-execution"
        for f in repo.findings
    )
    path = repository / "playbooks/check/PLAYBOOK.md"
    path.write_text(path.read_text().replace("beta_kernel.v1", "another_missing_kernel.v1"))
    write_index(repository)
    assert load_repository(repository).failures


@pytest.mark.parametrize(
    "target",
    [
        None,
        "../absent/PLAYBOOK.md",
        "PLAYBOOK.md",
        "../../../outside.md",
        "../../skills/testing/check/SKILL.md",
    ],
)
def test_superseded_playbook_requires_real_distinct_registered_replacement(
    repository: Path, target: str | None
) -> None:
    supersede_test_playbook(repository, target)
    with pytest.raises(StructureError):
        load_repository(repository)


def test_superseded_replacement_must_be_agents_linked(repository: Path) -> None:
    supersede_test_playbook(repository, "../check/PLAYBOOK.md")
    agents = repository / "AGENTS.md"
    agents.write_text(
        "\n".join(
            line
            for line in agents.read_text().splitlines()
            if "playbooks/check/PLAYBOOK.md" not in line
        )
        + "\n"
    )
    with pytest.raises(StructureError, match="linked by AGENTS"):
        load_repository(repository)


def test_authorized_guide_supersession_preserves_original_bytes() -> None:
    current = (ROOT / "playbooks/microservice-build/PLAYBOOK.md").read_text()
    notice = (
        "> **Historical guide — superseded, not executable.** Use the existing\n"
        "> [New Constellation Node playbook](../new-constellation-node/PLAYBOOK.md) for the\n"
        "> active node-build workflow. The original requirements and 17-step design below\n"
        "> are preserved for provenance; unavailable dependencies and step files are not\n"
        "> implemented or certified by structural CI. This does not claim that the active\n"
        "> replacement implements every proposed capability of this historical design.\n\n"
    )
    assert current.count(notice) == 1
    original = current.replace(notice, "").replace("status: superseded\n", "status: active\n", 1)
    original = original.replace("superseded_by: ../new-constellation-node/PLAYBOOK.md\n", "", 1)
    # Hash of the immutable historical source at fecdd927, not a content-eval verdict.
    assert hashlib.sha256(original.encode()).hexdigest() == (
        "5f0d60e026373bb7aa744b9ad8e26750f117c2dbe1da1b959bc5a0641cc4f8b6"
    )


def test_superseded_replacement_missing_step_still_fails(repository: Path) -> None:
    supersede_test_playbook(repository, "../check/PLAYBOOK.md")
    (repository / "playbooks/check/steps/run.md").unlink()
    write_index(repository)
    assert any(f.check == "declared-step" for f in load_repository(repository).failures)


def test_superseded_replacement_cycle_fails(repository: Path) -> None:
    supersede_test_playbook(repository, "../check/PLAYBOOK.md")
    target = repository / "playbooks/check/PLAYBOOK.md"
    target.write_text(
        target.read_text().replace(
            "name: check-playbook\n",
            "name: check-playbook\nstatus: superseded\nsuperseded_by: ../old/PLAYBOOK.md\n",
        )
    )
    write_index(repository)
    with pytest.raises(StructureError):
        load_repository(repository)


def test_superseded_replacement_escaping_symlink_fails(repository: Path, tmp_path: Path) -> None:
    supersede_test_playbook(repository, "../check/PLAYBOOK.md")
    target = repository / "playbooks/check/PLAYBOOK.md"
    target.unlink()
    target.symlink_to(put(tmp_path, "external.md", "# Not a repository artifact\n"))
    with pytest.raises(StructureError, match="escapes"):
        load_repository(repository)
