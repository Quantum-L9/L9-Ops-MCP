"""Regression tests: auxiliary validators fail closed and check structure (WU-37).

Each counterexample below passed at fecdd927: a missing input directory, a key
that only appears as a substring of another key or of a comment, a ``.yaml``
workflow that was never scanned, an unquoted YAML date that was never stale,
and validators that resolved their inputs from the caller's working directory.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import validate_command_parity  # noqa: E402
import validate_helpers  # noqa: E402
import validate_org_invariants  # noqa: E402
import validate_playbooks  # noqa: E402
import validate_skill_installability  # noqa: E402


def _run(script: str, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


COMPLETE_SKILL = """---
title: t
purpose: p
summary: s
version: 1.0.0
retrieval_keys: [k]
trigger_description: Use when testing.
---
body
"""


# --- skill_endpoint_audit ----------------------------------------------------


def test_skill_endpoint_audit_exits_1_on_failures_without_flag(tmp_path: Path) -> None:
    _write(tmp_path / "skills" / "a" / "SKILL.md", "---\ntitle: only\n---\n")
    proc = _run("skill_endpoint_audit.py", "--skills-dir", str(tmp_path / "skills"), cwd=tmp_path)
    assert proc.returncode == 1, proc.stdout
    flagged = _run(
        "skill_endpoint_audit.py",
        "--skills-dir",
        str(tmp_path / "skills"),
        "--exit-on-failure",
        cwd=tmp_path,
    )
    assert flagged.returncode == 1


def test_skill_endpoint_audit_passes_complete_skill(tmp_path: Path) -> None:
    _write(tmp_path / "skills" / "a" / "SKILL.md", COMPLETE_SKILL)
    proc = _run("skill_endpoint_audit.py", "--skills-dir", str(tmp_path / "skills"), cwd=tmp_path)
    assert proc.returncode == 0, proc.stdout


@pytest.mark.parametrize(
    "content",
    ["---\njust a scalar\n---\nbody\n", "no frontmatter at all\n", "---\n: [unclosed\n---\n"],
)
def test_skill_endpoint_audit_fails_on_unusable_frontmatter(tmp_path: Path, content: str) -> None:
    _write(tmp_path / "skills" / "a" / "SKILL.md", content)
    proc = _run("skill_endpoint_audit.py", "--skills-dir", str(tmp_path / "skills"), cwd=tmp_path)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "Traceback" not in proc.stderr


def test_skill_endpoint_audit_fails_on_missing_or_empty_dir(tmp_path: Path) -> None:
    missing = _run("skill_endpoint_audit.py", "--skills-dir", str(tmp_path / "nope"), cwd=tmp_path)
    assert missing.returncode == 1
    (tmp_path / "empty").mkdir()
    empty = _run("skill_endpoint_audit.py", "--skills-dir", str(tmp_path / "empty"), cwd=tmp_path)
    assert empty.returncode == 1


def test_skill_endpoint_audit_resolves_default_from_repo_root(tmp_path: Path) -> None:
    proc = _run("skill_endpoint_audit.py", cwd=tmp_path)
    assert "Found 0 skill files" not in proc.stdout
    assert proc.returncode == (1 if "FAIL:" in proc.stdout else 0), proc.stdout


# --- validate_headers ----------------------------------------------------------


def test_validate_headers_missing_dir_fails(tmp_path: Path) -> None:
    proc = _run(
        "validate_headers.py",
        "--dir",
        str(tmp_path / "missing"),
        "--required",
        "title",
        cwd=tmp_path,
    )
    assert proc.returncode != 0, proc.stdout


def test_validate_headers_dir_without_matching_files_fails(tmp_path: Path) -> None:
    _write(tmp_path / "d" / "x.txt", "title: x\n")
    proc = _run(
        "validate_headers.py", "--dir", str(tmp_path / "d"), "--required", "title", cwd=tmp_path
    )
    assert proc.returncode != 0, proc.stdout


def test_validate_headers_requires_structural_non_empty_field(tmp_path: Path) -> None:
    _write(tmp_path / "d" / "a.yaml", "display_name: x\ntitle:\n")
    proc = _run(
        "validate_headers.py",
        "--dir",
        str(tmp_path / "d"),
        "--required",
        "name,title",
        cwd=tmp_path,
    )
    assert proc.returncode == 1
    assert "'name'" in proc.stdout and "'title'" in proc.stdout


def test_validate_headers_reads_html_comment_meta_block(tmp_path: Path) -> None:
    _write(tmp_path / "d" / "k.md", "<!-- L9_META\ntitle: k\nring: R5\n/L9_META -->\n# body\n")
    proc = _run(
        "validate_headers.py",
        "--dir",
        str(tmp_path / "d"),
        "--ext",
        ".md",
        "--required",
        "title,ring",
        cwd=tmp_path,
    )
    assert proc.returncode == 0, proc.stdout


def test_validate_headers_relative_dir_resolves_from_repo_root(tmp_path: Path) -> None:
    proc = _run(
        "validate_headers.py", "--dir", "docs/kernels", "--required", "kernel_id", cwd=tmp_path
    )
    assert "not found" not in proc.stdout
    assert "docs/kernels" in proc.stdout


# --- harvest_audit -------------------------------------------------------------


def test_harvest_audit_missing_source_fails(tmp_path: Path) -> None:
    proc = _run(
        "harvest_audit.py",
        "--source",
        str(tmp_path / "absent.yaml"),
        "--check-fields",
        "a",
        cwd=tmp_path,
    )
    assert proc.returncode != 0, proc.stdout


def test_harvest_audit_substring_mention_is_not_coverage(tmp_path: Path) -> None:
    src = _write(tmp_path / "k.yaml", "kernel_id: k\n# ring is described in prose only\n")
    proc = _run(
        "harvest_audit.py", "--source", str(src), "--check-fields", "kernel_id,ring", cwd=tmp_path
    )
    assert proc.returncode == 1, proc.stdout
    assert "ring" in proc.stdout


def test_harvest_audit_covered_fields_pass(tmp_path: Path) -> None:
    src = _write(tmp_path / "k.yaml", "kernel_id: k\nring: R5\n")
    proc = _run(
        "harvest_audit.py", "--source", str(src), "--check-fields", "kernel_id,ring", cwd=tmp_path
    )
    assert proc.returncode == 0, proc.stdout


# --- validate_skill_installability -------------------------------------------


def _fails(lines: list[str]) -> list[str]:
    return [line for line in lines if line.startswith("FAIL")]


def test_skill_installability_display_name_is_not_name(tmp_path: Path) -> None:
    _write(tmp_path / "s" / "SKILL.md", "---\ndisplay_name: x\ndescription: Use when y.\n---\n")
    fails = _fails(validate_skill_installability.check_skill(tmp_path / "s"))
    assert any("name" in line for line in fails), fails


def test_skill_installability_trigger_description_is_not_description(tmp_path: Path) -> None:
    _write(tmp_path / "s" / "SKILL.md", "---\nname: x\ntrigger_description: Use when y.\n---\n")
    fails = _fails(validate_skill_installability.check_skill(tmp_path / "s"))
    assert any("description" in line for line in fails), fails


def test_skill_installability_accepts_structural_frontmatter(tmp_path: Path) -> None:
    _write(tmp_path / "s" / "SKILL.md", "---\nname: x\ndescription: Use when y.\n---\nbody\n")
    assert _fails(validate_skill_installability.check_skill(tmp_path / "s")) == []


# --- validate_playbooks --------------------------------------------------------


def test_playbook_handoff_schema_requires_structural_keys(tmp_path: Path) -> None:
    pb = tmp_path / "playbooks" / "p"
    _write(pb / "PLAYBOOK.md", "# p\n")
    (pb / "steps").mkdir()
    _write(pb / "handoffs" / "x.schema.yaml", "# required: nothing here\nfoo: properties\n")
    assert validate_playbooks.main(root=tmp_path) == 1


def test_playbook_handoff_schema_with_properties_passes(tmp_path: Path) -> None:
    pb = tmp_path / "playbooks" / "p"
    _write(pb / "PLAYBOOK.md", "# p\n")
    (pb / "steps").mkdir()
    _write(pb / "handoffs" / "x.schema.yaml", "type: object\nproperties:\n  a: {type: string}\n")
    assert validate_playbooks.main(root=tmp_path) == 0


# --- validate_org_invariants ---------------------------------------------------


def test_org_invariant_comment_does_not_satisfy_owner(tmp_path: Path) -> None:
    _write(
        tmp_path / "ORG_INVARIANTS.yaml",
        "# owner: Quantum-L9\norg_invariants:\n  owner: someone-else\n"
        "  repo_birth:\n    allowed_owner: someone-else\n",
    )
    assert validate_org_invariants.main(root=tmp_path) == 1


def test_org_invariant_structural_owner_passes(tmp_path: Path) -> None:
    _write(
        tmp_path / "ORG_INVARIANTS.yaml",
        "---\nl9_schema: 1\n---\norg_invariants:\n  owner: Quantum-L9\n"
        "  repo_birth:\n    allowed_owner: Quantum-L9\n",
    )
    assert validate_org_invariants.main(root=tmp_path) == 0


def test_org_invariants_repository_file_passes() -> None:
    assert validate_org_invariants.main() == 0


# --- validate_command_parity / validate_helpers ------------------------------


def _parity_root(tmp_path: Path, makefile: str, readme: str = "") -> Path:
    _write(tmp_path / "Makefile", makefile)
    _write(tmp_path / "README.md", readme)
    return tmp_path


def test_command_parity_scans_yaml_workflows(tmp_path: Path) -> None:
    root = _parity_root(tmp_path, "ci:\n\ttrue\n")
    _write(
        root / ".github" / "workflows" / "x.yaml",
        "jobs:\n  a:\n    steps:\n      - run: make gone\n",
    )
    assert validate_command_parity.main(root=root) == 1


def test_command_parity_requires_makefile_and_readme(tmp_path: Path) -> None:
    assert validate_command_parity.main(root=tmp_path) == 1


def test_command_parity_variable_assignment_is_not_a_target(tmp_path: Path) -> None:
    root = _parity_root(tmp_path, "FOO := bar\nci:\n\ttrue\n", "```bash\nmake FOO\n```\n")
    assert validate_command_parity.main(root=root) == 1


def test_command_parity_ignores_prose_make(tmp_path: Path) -> None:
    root = _parity_root(
        tmp_path, "ci:\n\ttrue\n", "Run `make ci`; make sure the tree is clean.\n\n    make ci\n"
    )
    assert validate_command_parity.main(root=root) == 0


def test_extract_make_targets_handles_multi_target_rules() -> None:
    targets = validate_helpers.extract_make_targets(
        ".DEFAULT_GOAL := help\nPY ?= python3\na b: dep\n\techo\n.PHONY: a b\n"
    )
    assert targets == {"a", "b"}


# --- library_health ------------------------------------------------------------


KERNEL_OK = "retrieval_keys: [k]\nring: R5\nproduction_ready: true\n"


def test_library_health_unquoted_date_is_stale(tmp_path: Path) -> None:
    _write(tmp_path / "docs" / "kernels" / "k.yaml", KERNEL_OK + "last_tested: 2020-01-01\n")
    proc = _run(
        "library_health.py",
        "--root",
        str(tmp_path),
        "--report",
        str(tmp_path / "r.md"),
        cwd=tmp_path,
    )
    assert proc.returncode == 1
    assert "STALE" in proc.stdout + (tmp_path / "r.md").read_text()


def test_library_health_fresh_kernel_passes(tmp_path: Path) -> None:
    _write(tmp_path / "docs" / "kernels" / "k.yaml", KERNEL_OK + 'last_tested: "2999-01-01"\n')
    proc = _run(
        "library_health.py",
        "--root",
        str(tmp_path),
        "--report",
        str(tmp_path / "r.md"),
        cwd=tmp_path,
    )
    assert proc.returncode == 0, proc.stdout


def test_library_health_empty_root_fails(tmp_path: Path) -> None:
    proc = _run(
        "library_health.py",
        "--root",
        str(tmp_path),
        "--report",
        str(tmp_path / "r.md"),
        cwd=tmp_path,
    )
    assert proc.returncode == 1, proc.stdout


def test_library_health_default_scans_repo_not_cwd(tmp_path: Path) -> None:
    proc = _run("library_health.py", "--report", str(tmp_path / "r.md"), cwd=tmp_path)
    assert "scanned 0 files" not in proc.stdout
    assert "scanned" in proc.stdout
