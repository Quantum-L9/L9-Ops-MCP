"""admission.py writes memory content under logs/ and memory_quarantine/ relative
to the working directory; a test run from the repo root must not leave either
committable.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _ignored(path: str) -> bool:
    result = subprocess.run(  # noqa: S603 — fixed git argv
        ["git", "check-ignore", "--quiet", "--no-index", path],  # noqa: S607
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode in (0, 1), result.stderr
    return result.returncode == 0


@pytest.mark.parametrize(
    "path",
    ["logs/memory-admission-log.jsonl", "memory_quarantine/abc123.json"],
)
def test_admission_runtime_output_is_ignored(path: str) -> None:
    assert _ignored(path), f"{path} is not git-ignored"


@pytest.mark.parametrize("path", ["src/logs/x.py", "docs/memory_quarantine/x.md"])
def test_ignore_is_root_anchored(path: str) -> None:
    assert not _ignored(path), f"{path} should not be ignored"
