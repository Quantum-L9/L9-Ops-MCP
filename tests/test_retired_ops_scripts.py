"""Regression tests for operational scripts retired by owner decision.

Each retired script performed a consequential write outside this repository's
control (remote GitHub admin APIs, another repository's files) without a guard.
Retirement is the recorded remediation, so the regression is: the script is
gone and no executable surface of this repository still invokes it.

Inventory ledgers (provenance maps, retrieval index, manifest) describe history
and are maintained by their own tooling; they are not executable surfaces.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Paths whose content is executed or drives execution (CI, make, install, hooks).
EXECUTABLE_SURFACES: tuple[str, ...] = (
    "scripts",
    "src",
    ".github",
    "Makefile",
    "assets/Makefile",
    ".pre-commit-config.yaml",
    "pyproject.toml",
)

# (retired path, decision) pairs.
RETIRED: tuple[tuple[str, str], ...] = (
    # D-17 A: unguarded, non-idempotent ruleset POST to repos/cryptoxdog/L9.
    ("scripts/DEPLOY_ADDITIONS.sh", "D-17"),
    # D-16 A: logged secrets, wrote during "dry-run" preflight, targeted a
    # foreign repository layout (.github/scripts, tests_l11/).
    ("scripts/DEPLOY-v3.3.sh", "D-16"),
    # D-14 A: patched another repository's context-extractor.py with an
    # unanchored regex (SyntaxError / truncated function) and reported success.
    ("scripts/wire_governance_sink.py", "D-14"),
)


def _tracked_files_referencing(needle: str) -> list[str]:
    surfaces = [s for s in EXECUTABLE_SURFACES if (REPO_ROOT / s).exists()]
    proc = subprocess.run(
        ["git", "grep", "-l", "-F", needle, "--", *surfaces],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    # git grep: 0 = matches, 1 = no match, >1 = error.
    if proc.returncode > 1:
        pytest.fail(f"git grep failed: {proc.stderr.strip()}")
    return [line for line in proc.stdout.splitlines() if line]


@pytest.mark.parametrize(("path", "decision"), RETIRED)
def test_retired_script_is_absent(path: str, decision: str) -> None:
    assert not (REPO_ROOT / path).exists(), f"{path} must be retired ({decision} A)"


@pytest.mark.parametrize(("path", "decision"), RETIRED)
def test_retired_script_is_not_invoked(path: str, decision: str) -> None:
    name = Path(path).name
    this_file = Path(__file__).resolve().relative_to(REPO_ROOT).as_posix()
    hits = [p for p in _tracked_files_referencing(name) if p != this_file]
    assert hits == [], f"{name} ({decision}) still referenced by: {hits}"


def test_install_and_preflight_do_not_depend_on_the_retired_governance_sink() -> None:
    """D-14 A: nothing in this repository installs graphiti_sink.py any more."""
    for script in ("scripts/install.sh", "scripts/preflight.sh"):
        text = (REPO_ROOT / script).read_text(encoding="utf-8")
        assert "graphiti_sink" not in text, f"{script} still wires or checks graphiti_sink"
