# --- L9_META ---
# l9_schema: 1
# artifact_type: test
# tags: [ci-proof, repository-execution]
# retrieval: on_demand
# status: active
# --- /L9_META ---

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_contract_is_exact_v2() -> None:
    contract = json.loads((ROOT / ".l9/repo-workflow.json").read_text())
    assert contract == {
        "schema": "l9.repo-execution/v2",
        "facade": "make-v1",
        "required_phases": ["setup", "validate", "check", "test"],
    }


def test_full_test_phase_executes_both_suites() -> None:
    result = subprocess.run(["make", "-n", "test"], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert "-m pytest tests scripts -q" in result.stdout
    assert "--co" not in result.stdout
    assert "|| true" not in result.stdout


def test_failed_test_command_blocks_phase() -> None:
    result = subprocess.run(["make", "test", "PYTHON=false"], cwd=ROOT, capture_output=True)
    assert result.returncode != 0


def test_ci_stops_before_later_phases_when_validation_fails() -> None:
    result = subprocess.run(
        ["make", "ci", "PYTHON=false"], cwd=ROOT, text=True, capture_output=True
    )
    assert result.returncode != 0
    assert "false scripts/validate_wiring.py --all" in result.stdout
    assert "-m pytest" not in result.stdout
    assert "-m ruff" not in result.stdout


def test_l11_fast_tests_are_executed_not_only_collected() -> None:
    workflow = (ROOT / ".github/workflows/08-L11-CI-WORKFLOW-v3.3.yaml").read_text()
    fast_step = workflow.split("- name: pytest (fast)", 1)[1].split("- name:", 1)[0]
    assert 'pytest tests/ -m "not slow" --tb=short -q' in fast_step
    assert "--co" not in fast_step
    assert "||" not in fast_step
