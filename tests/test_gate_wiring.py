"""Regression tests for the repository gate wiring (WU-36, D-13 C).

The pre-commit hooks, the governance workflow and the Makefile must only
invoke tools that run against repository content.  ``validate_wiring.py`` and
``impact_analysis.py`` read a root ``MANIFEST.json`` that does not exist, so
they crashed on every commit (pre-commit) and were permanently skipped in CI.
They are retired together with every caller.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PRECOMMIT = ROOT / ".pre-commit-config.yaml"
GOVERNANCE = ROOT / ".github" / "workflows" / "governance.yml"
MAKEFILE = ROOT / "Makefile"

RETIRED = ("validate_wiring.py", "impact_analysis.py")
_SCRIPT_CMD = re.compile(
    r"\b(python3|python|bash)\s+(scripts/[A-Za-z0-9_./-]+)((?:\s+--?[A-Za-z0-9_.=-]+)*)"
)


def _precommit_entries() -> list[str]:
    config = yaml.safe_load(PRECOMMIT.read_text(encoding="utf-8"))
    return [hook["entry"] for repo in config["repos"] for hook in repo["hooks"]]


def _governance_run_blocks() -> list[str]:
    workflow = yaml.safe_load(GOVERNANCE.read_text(encoding="utf-8"))
    return [
        step["run"]
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if "run" in step
    ]


def _gate_script_commands() -> list[tuple[str, str, list[str]]]:
    """Script invocations made by pre-commit hooks and the governance job."""
    commands: list[tuple[str, str, list[str]]] = []
    texts = _precommit_entries() + _governance_run_blocks()
    for text in texts:
        for interp, script, args in _SCRIPT_CMD.findall(text):
            commands.append((interp, script, args.split()))
    return commands


def test_retired_tools_have_no_callers() -> None:
    for path in (PRECOMMIT, GOVERNANCE, MAKEFILE):
        text = path.read_text(encoding="utf-8")
        for name in RETIRED:
            assert name not in text, f"{path.name} still references retired {name}"
    for name in RETIRED:
        assert not (ROOT / "scripts" / name).exists(), f"scripts/{name} should be retired"


def test_every_referenced_script_exists() -> None:
    texts = [
        PRECOMMIT.read_text(encoding="utf-8"),
        GOVERNANCE.read_text(encoding="utf-8"),
        MAKEFILE.read_text(encoding="utf-8"),
    ]
    for text in texts:
        for _interp, script, _args in _SCRIPT_CMD.findall(text):
            assert (ROOT / script).is_file(), f"referenced script {script} is missing"


def test_governance_has_no_presence_conditional_skip() -> None:
    """A step guarded by a file test on an absent path is a permanent skip."""
    guard = re.compile(r"if\s+\[\s+-[fed]\s+([^\s\]]+)\s+\]")
    for block in _governance_run_blocks():
        for path in guard.findall(block):
            assert (ROOT / path).exists(), (
                f"governance step is conditional on absent {path}: permanently skipped"
            )


@pytest.mark.parametrize(
    ("interp", "script", "args"),
    _gate_script_commands(),
    ids=lambda v: v if isinstance(v, str) else " ".join(v),
)
def test_gate_commands_run_without_crashing(interp: str, script: str, args: list[str]) -> None:
    """Every gate command runs and reports; none dies with a traceback."""
    exe = [sys.executable] if interp.startswith("python") else ["bash"]
    proc = subprocess.run(
        [*exe, script, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    output = proc.stdout + proc.stderr
    assert "Traceback (most recent call last)" not in output, output[-2000:]
    assert proc.returncode in (0, 1), f"{script} exit {proc.returncode}: {output[-2000:]}"
