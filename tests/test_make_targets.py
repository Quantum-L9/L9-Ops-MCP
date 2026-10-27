"""Regression tests: documented Makefile / pre-commit targets are runnable and
``make ci`` fails when its checks fail (WU-40, D-15 A).

At fecdd927 ``make ci`` appended ``|| true`` to ruff and pytest, ``preflight``
refused the (mode 100644) script, ``eval`` pointed at an absent root
``evals/`` config, five ``pr-fix*`` targets called a non-existent
``pr_repair`` package, and two pre-commit hooks filtered on a non-existent
``kernels/optimized/`` path.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"

pytestmark = pytest.mark.skipif(shutil.which("make") is None, reason="GNU make not installed")


def _make(*args: str, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", "--no-print-directory", *args, f"PYTHON={sys.executable}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _recipes() -> dict[str, list[str]]:
    recipes: dict[str, list[str]] = {}
    current: str | None = None
    for line in MAKEFILE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Za-z0-9_.-]+):(?!=)", line)
        if match:
            current = match.group(1)
            recipes[current] = []
        elif line.startswith("\t") and current:
            recipes[current].append(line.strip())
        elif line and not line.startswith("\t"):
            current = None
    return recipes


def test_ci_recipe_does_not_swallow_failures() -> None:
    for target in ("ci", "lint", "typecheck", "test"):
        for line in _recipes()[target]:
            assert "|| true" not in line, f"{target}: {line}"
            assert not line.startswith("-"), f"{target} ignores errors: {line}"


def test_make_ci_fails_on_failing_test(tmp_path: Path) -> None:
    failing = tmp_path / "test_injected_failure.py"
    failing.write_text("def test_injected():\n    assert False\n", encoding="utf-8")
    proc = _make("ci", "CI_STEPS=test", f"TEST_PATHS={failing}")
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert "1 failed" in proc.stdout


def test_make_ci_passes_on_passing_test(tmp_path: Path) -> None:
    passing = tmp_path / "test_injected_pass.py"
    passing.write_text("def test_injected():\n    assert True\n", encoding="utf-8")
    proc = _make("ci", "CI_STEPS=test", f"TEST_PATHS={passing}")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_make_ci_runs_every_gate_step() -> None:
    proc = _make("-n", "ci")
    assert proc.returncode == 0, proc.stderr
    for fragment in (
        "scripts/library_health.sh",
        "scripts/enforce_progressive_disclosure.sh",
        "scripts/audit_hardban_duplication.sh",
        "scripts/convergence_tracker.py",
        "scripts/validate_pyproject_entrypoints.py",
        "check src scripts tests",
        "format --check src scripts tests",
        "-m pytest",
    ):
        assert fragment in proc.stdout, fragment


def test_make_lint_fails_on_lint_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text("import os\n", encoding="utf-8")
    proc = _make("lint", f"LINT_PATHS={bad}")
    assert proc.returncode != 0, proc.stdout + proc.stderr


def test_make_lint_fails_visibly_without_ruff() -> None:
    proc = _make("lint", "RUFF=/nonexistent/ruff")
    assert proc.returncode != 0
    assert "ruff" in (proc.stdout + proc.stderr)


def test_make_preflight_executes_script(tmp_path: Path) -> None:
    stub = tmp_path / "preflight.sh"
    stub.write_text("echo PREFLIGHT-STUB-RAN\n", encoding="utf-8")
    stub.chmod(0o644)
    proc = _make("preflight", f"PREFLIGHT_SCRIPT={stub}")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PREFLIGHT-STUB-RAN" in proc.stdout


def test_eval_config_exists_and_matches_ci() -> None:
    dry_run = _make("-n", "eval")
    assert dry_run.returncode == 0, dry_run.stderr
    make_cfg = [c.rstrip(";") for c in re.findall(r"--config\s+(\S+)", dry_run.stdout)]
    workflow = (ROOT / ".github" / "workflows" / "governance.yml").read_text(encoding="utf-8")
    ci_cfg = re.findall(r"promptfoo eval --config\s+(\S+)", workflow)
    assert make_cfg and ci_cfg
    assert set(make_cfg) == set(ci_cfg)
    for cfg in make_cfg:
        assert (ROOT / cfg).is_file(), cfg


# Installer/test-runner modules come from the environment; a missing one fails
# visibly at run time.  Every other ``-m`` module must be importable here.
ENVIRONMENT_TOOLS = {"pip", "pytest"}


def test_recipe_modules_and_scripts_exist() -> None:
    src = ROOT / "src"
    sys.path.insert(0, str(src))
    try:
        for target, lines in _recipes().items():
            for line in lines:
                for module in re.findall(r"-m\s+([A-Za-z_][\w.]*)", line):
                    if module in ENVIRONMENT_TOOLS:
                        continue
                    assert importlib.util.find_spec(module) is not None, f"{target}: {module}"
                for script in re.findall(r"(?:\$\(PYTHON\)|bash)\s+(scripts/\S+)", line):
                    assert (ROOT / script).is_file(), f"{target}: {script}"
    finally:
        sys.path.remove(str(src))
    assert not any(t.startswith("pr-fix") for t in _recipes())


def test_phony_lists_only_defined_targets() -> None:
    text = MAKEFILE.read_text(encoding="utf-8").replace("\\\n", " ")
    phony = re.search(r"^\.PHONY:(.*)$", text, re.MULTILINE)
    assert phony is not None
    defined = set(_recipes())
    for name in phony.group(1).split():
        assert name in defined, f".PHONY names undefined target {name}"


def test_precommit_file_filters_match_repository_files() -> None:
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    kernels = [f for f in tracked if re.match(r"^docs/kernels/.*\.yaml$", f)]
    assert kernels
    for repo in config["repos"]:
        for hook in repo["hooks"]:
            pattern = hook.get("files")
            if pattern is None:
                continue
            matched = [f for f in tracked if re.search(pattern, f)]
            assert matched, f"{hook['id']}: files filter {pattern!r} matches nothing"
            if hook["id"] in {"l9-progressive-disclosure", "l9-hardban-audit"}:
                assert all(re.search(pattern, k) for k in kernels), hook["id"]
