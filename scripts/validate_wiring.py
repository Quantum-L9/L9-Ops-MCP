# --- L9_META ---
# l9_schema: 1
# component: validate_wiring
# artifact_type: context
# tags: [validation, wiring]
# retrieval: on_demand
# status: active
# --- /L9_META ---
"""Validate actual repository wiring, not authored completeness or content evals.

The consolidated repository uses AGENTS, the canonical runtime kernel registry,
its integrity index, and declared artifact references. Typed legacy root manifests
remain supported; missing/unknown/empty authority never becomes a zero-check pass.
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path

import yaml

try:
    from .repo_structure import ROOT, Repository, StructureError, load_repository
    from .validate_helpers import extract_make_targets, read_makefile_tree
except ImportError:  # Direct CLI execution from any working directory.
    from repo_structure import ROOT, Repository, StructureError, load_repository
    from validate_helpers import extract_make_targets, read_makefile_tree

LIBRARY_ROOT = ROOT

# Literal interpreter script invocations, including Make's declared Python variable.
SCRIPT_COMMAND = re.compile(
    r"(?:\bpython(?:3(?:\.\d+)?)?|\$\(PYTHON\)|\bbash|\bsh)\s+"
    r"(?:-[A-Za-z]+\s+)*[\"']?([A-Za-z0-9_./-]+\.(?:py|sh))\b"
)
DIRECT_SCRIPT = re.compile(r"(?:^|[;&|\s])(?:\./)((?:scripts|ci)/[A-Za-z0-9_./-]+\.(?:py|sh))\b")


def _scripts(repo: Repository, text: str, source: str) -> int:
    references = set(SCRIPT_COMMAND.findall(text)) | set(DIRECT_SCRIPT.findall(text))
    for rel in sorted(references):
        # A same-path literal existence guard makes an absent upstream script
        # inapplicable, not an active command. Authority cannot be skipped this
        # way: this validator always loads and validates the real repository.
        escaped = re.escape(rel)
        guard_pattern = re.compile(
            rf"(?:if|elif)\s+\[\s+-[fx]\s+[\"']?{escaped}[\"']?\s*\]\s*;\s*then"
            rf"(?:(?!\b(?:else|elif|fi)\b).)*",
            re.S,
        )
        guarded = guard_pattern.findall(text)
        unguarded_text = guard_pattern.sub("", text)
        unguarded_references = set(SCRIPT_COMMAND.findall(unguarded_text)) | set(
            DIRECT_SCRIPT.findall(unguarded_text)
        )
        if guarded and rel not in unguarded_references and not (repo.root / rel).is_file():
            repo.record(
                "NOT_APPLICABLE_WITH_REASON",
                f"optional-command ({source})",
                f"{rel}: absent and invocation has a same-path literal existence guard",
            )
            continue
        repo.check_reference(rel, f"command-script ({source})")
    return len(references)


def validate_commands(repo: Repository) -> None:
    """Static command reference checks; never execute Make or workflow recipes."""
    try:
        make_text = read_makefile_tree(repo.root / "Makefile")
    except (OSError, ValueError) as exc:
        repo.record("FAIL", "make-includes", str(exc))
        return
    targets = extract_make_targets(make_text)
    if not targets:
        repo.record("FAIL", "make-targets", "no declared Make targets")
    else:
        repo.record("PASS", "make-targets", f"{len(targets)} targets from contained includes")
    recipes = "\n".join(line for line in make_text.splitlines() if line.startswith("\t"))
    command_count = _scripts(repo, recipes, "Makefile/includes")
    workflow_dir = repo.root / ".github/workflows"
    workflows = sorted(p for p in workflow_dir.glob("*") if p.suffix in (".yaml", ".yml"))
    if not workflows:
        repo.record("FAIL", "workflows", "no .yaml/.yml workflows found")
    for workflow in workflows:
        try:
            data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
            if (
                not isinstance(data, dict)
                or not isinstance(data.get("jobs"), dict)
                or not data["jobs"]
            ):
                raise StructureError("workflow requires a nonempty jobs mapping")
            for job_id, job in data["jobs"].items():
                if not isinstance(job, dict):
                    raise StructureError(f"job {job_id} must be a mapping")
                # Reusable workflow jobs legitimately have uses instead of steps.
                steps = job.get("steps", [])
                if not isinstance(steps, list):
                    raise StructureError(f"job {job_id} steps must be a list")
                for step in steps:
                    if not isinstance(step, dict):
                        raise StructureError(f"job {job_id}: step must be a mapping")
                    run = step.get("run")
                    if run is not None:
                        if not isinstance(run, str):
                            raise StructureError(f"job {job_id}: run must be a string")
                        command_count += _scripts(repo, run, workflow.name)
                    uses = step.get("uses", "")
                    if isinstance(uses, str) and uses.startswith("./"):
                        from_path = (repo.root / uses).resolve()
                        if not from_path.is_relative_to(repo.root) or not from_path.is_dir():
                            repo.record("FAIL", "local-action", f"invalid local action: {uses}")
                        elif not any(
                            (from_path / f"action.{suffix}").is_file() for suffix in ("yml", "yaml")
                        ):
                            repo.record(
                                "FAIL", "local-action", f"missing action.yml/action.yaml: {uses}"
                            )
                        else:
                            repo.record("PASS", "local-action", uses)
            repo.record("PASS", "workflow-structure", workflow.relative_to(repo.root).as_posix())
        except (OSError, ValueError, yaml.YAMLError) as exc:
            repo.record("FAIL", "workflow-structure", f"{workflow.name}: {exc}")
    if not command_count:
        repo.record(
            "FAIL", "command-script-inventory", "no repository scripts referenced by build/CI"
        )
    else:
        repo.record(
            "PASS", "command-script-inventory", f"{command_count} literal script references checked"
        )
    syntax_paths = set()
    for directory in ("scripts", "src", "tests"):
        syntax_paths.update((repo.root / directory).rglob("*.py"))
    for path in sorted(syntax_paths):
        try:
            # Check containment before reading a symlinked Python source.
            if not path.resolve().is_relative_to(repo.root):
                raise StructureError("Python source escapes repository")
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, ValueError, SyntaxError) as exc:
            repo.record("FAIL", "python-syntax", f"{path.relative_to(repo.root)}: {exc}")
    if syntax_paths:
        repo.record(
            "PASS",
            "python-syntax-inventory",
            f"{len(syntax_paths)} Python files parsed; see failures",
        )
    else:
        repo.record("FAIL", "python-syntax-inventory", "no Python files found")


def run_existing_validators(repo: Repository) -> None:
    """Reuse callable/import and command-parity authorities, with explicit cwd."""
    for name in ("validate_command_parity.py", "validate_pyproject_entrypoints.py"):
        validator = repo.root / "scripts" / name
        if not validator.is_file():
            repo.record("FAIL", "validator", f"missing scripts/{name}")
            continue
        try:
            proc = subprocess.run(
                [sys.executable, str(validator)],
                cwd=repo.root,
                text=True,
                capture_output=True,
                timeout=60,
            )
            output = (proc.stdout + proc.stderr).strip()
            # Preserve the existing validator's details, not only its return code.
            for line in output.splitlines():
                status, separator, detail = line.partition(":")
                if separator and status in (
                    "PASS",
                    "FAIL",
                    "BLOCKED",
                    "UNKNOWN",
                    "NOT_APPLICABLE_WITH_REASON",
                ):
                    repo.record(status, f"{name}-detail", detail.strip())
                else:
                    repo.record("UNKNOWN", f"{name}-detail", line)
            repo.record(
                "PASS" if proc.returncode == 0 else "FAIL",
                name,
                f"exit={proc.returncode}; {len(output.splitlines())} diagnostic lines",
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            repo.record("BLOCKED", name, str(exc))


def validate_repository(
    root: Path = ROOT, manifest: str | None = None, run_validators: bool = True
) -> Repository:
    repo = load_repository(root, manifest)
    validate_commands(repo)
    if run_validators:
        run_existing_validators(repo)
    return repo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all", action="store_true", help="check every registered artifact (default)"
    )
    parser.add_argument(
        "--id", help="artifact ID; consolidated skills/playbooks use scoped directory IDs"
    )
    parser.add_argument("--type", choices=("kernel", "skill", "playbook", "prompt"))
    parser.add_argument("--root", type=Path, default=LIBRARY_ROOT)
    parser.add_argument("--manifest", help="explicit contained legacy manifest path")
    args = parser.parse_args(argv)
    try:
        repo = validate_repository(args.root, args.manifest)
        selected = [
            a
            for a in repo.artifacts.values()
            if (not args.id or a.id == args.id) and (not args.type or a.kind == args.type)
        ]
        if not selected:
            raise StructureError("artifact selection is empty or unknown")
        # Selection is a reporting filter, never a way to ignore broken global authority.
        print(f"Source: {repo.source}")
        print(f"Artifacts selected: {len(selected)} / inventoried: {len(repo.artifacts)}")
        for finding in repo.findings:
            print(finding.line())
        passes = sum(f.status == "PASS" for f in repo.findings)
        print(
            f"Artifacts checked: {len(repo.artifacts)}; structural checks passed: {passes}; "
            f"wiring gaps: {len(repo.failures)}"
        )
        print(
            "FAIL: repository wiring has gaps"
            if repo.failures
            else "PASS: repository structural wiring"
        )
        return 1 if repo.failures or not passes else 0
    except Exception as exc:
        # Registry/schema/import failures must remain a failed gate, not a traceback-only skip.
        print(f"FAIL: repository-structure: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
