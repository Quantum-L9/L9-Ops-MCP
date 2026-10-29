"""Regression tests for scripts/convergence_tracker.py (WU-35: F-059, F-060).

The tracker must read the real kernel tree (``docs/kernels``), select a kernel
by its parsed ``kernel_id`` (not by substring), confine ``--update-kernel``
edits to that kernel's ``convergence_footer`` block, match footer fields by
anchored key, write the computed report, and exit non-zero when it finds no
kernels.

Every test runs a copy of the script inside a ``tmp_path`` tree; the
repository's ``docs/kernels/**`` is never edited.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "convergence_tracker.py"
REPO_KERNELS = REPO_ROOT / "docs" / "kernels"

TARGET = """\
kernel_id: target_kernel.v1
ring: R5
body:
  status: body-status-must-not-change
convergence_footer:
  review_status: pending
  status: active
  threshold: 0.05
  pass_count: 0
  final_ratio: 0.0
  unknowns:
    - "U-1: open"
post_footer:
  status: trailing-status-must-not-change
"""

DECOY = """\
kernel_id: decoy_kernel.v1
depends_on:
  - kernel_id: target_kernel.v1
convergence_footer:
  status: active
  threshold: 0.05
  final_ratio: 0.0
"""


def _tree(root: Path, kernels: dict[str, str] | None = None, copy_repo: bool = False) -> Path:
    (root / "scripts").mkdir(parents=True)
    shutil.copy2(SCRIPT, root / "scripts" / SCRIPT.name)
    kdir = root / "docs" / "kernels"
    if copy_repo:
        shutil.copytree(REPO_KERNELS, kdir)
    else:
        kdir.mkdir(parents=True)
    for rel, text in (kernels or {}).items():
        path = kdir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(root / "scripts" / SCRIPT.name), *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def _repo_kernel_ids() -> set[str]:
    ids: set[str] = set()
    for path in REPO_KERNELS.rglob("*.yaml"):
        for doc in yaml.safe_load_all(path.read_text(encoding="utf-8")):
            if isinstance(doc, dict) and isinstance(doc.get("kernel_id"), str):
                ids.add(doc["kernel_id"])
    return ids


def test_reports_the_docs_kernels_tree(tmp_path: Path) -> None:
    root = _tree(tmp_path / "lib", copy_repo=True)
    expected = _repo_kernel_ids()
    assert expected, "repository must contain YAML kernels"

    proc = _run(root, "--write-report")

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"Total kernels:   {len(expected)}" in proc.stdout
    report = yaml.safe_load((root / "evals" / "convergence-status.yaml").read_text())
    assert report["summary"]["total"] == len(expected)
    assert {k["kernelid"] for k in report["kernels"]} == expected
    for key in ("never_evaluated", "stale", "below_threshold", "current"):
        assert key in report["summary"]
    assert set(report["buckets"]) >= {"NEVER_EVALUATED", "STALE", "BELOW_THRESHOLD", "CURRENT"}


def test_no_kernels_found_exits_non_zero(tmp_path: Path) -> None:
    root = _tree(tmp_path / "lib")

    proc = _run(root)

    assert proc.returncode != 0
    assert "no kernels" in (proc.stdout + proc.stderr).lower()


def test_footer_fields_are_matched_by_anchored_key(tmp_path: Path) -> None:
    root = _tree(tmp_path / "lib", {"R5/target.yaml": TARGET})

    proc = _run(root, "--write-report")

    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = yaml.safe_load((root / "evals" / "convergence-status.yaml").read_text())
    (kernel,) = report["kernels"]
    assert kernel["kernelid"] == "target_kernel.v1"
    assert kernel["status"] == "active"  # not review_status's "pending"


def test_update_edits_only_the_named_kernel_footer(tmp_path: Path) -> None:
    # The decoy sorts first and mentions the target id: substring selection
    # picked it.
    root = _tree(tmp_path / "lib", {"R5/a_decoy.yaml": DECOY, "R5/target.yaml": TARGET})
    kdir = root / "docs" / "kernels" / "R5"

    proc = _run(
        root,
        "--update-kernel",
        "target_kernel.v1",
        "--pass-rate",
        "0.92",
        "--model",
        "claude-sonnet-4",
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (kdir / "a_decoy.yaml").read_text(encoding="utf-8") == DECOY
    doc = yaml.safe_load((kdir / "target.yaml").read_text(encoding="utf-8"))
    footer = doc["convergence_footer"]
    assert footer["status"] == "stable"
    assert footer["final_ratio"] == 0.92
    assert footer["review_status"] == "pending"
    assert footer["modelVersion"] == "claude-sonnet-4"
    assert str(footer["lastRunDate"])
    assert footer["unknowns"] == ["U-1: open"]
    assert doc["post_footer"]["status"] == "trailing-status-must-not-change"
    assert doc["body"]["status"] == "body-status-must-not-change"


def test_update_unknown_kernel_exits_non_zero_and_writes_nothing(tmp_path: Path) -> None:
    root = _tree(tmp_path / "lib", {"R5/a_decoy.yaml": DECOY})
    path = root / "docs" / "kernels" / "R5" / "a_decoy.yaml"

    proc = _run(root, "--update-kernel", "target_kernel.v1", "--pass-rate", "0.5")

    assert proc.returncode != 0
    assert path.read_text(encoding="utf-8") == DECOY


def test_update_refuses_a_kernel_that_resolves_outside_docs_kernels(tmp_path: Path) -> None:
    """Sonar pythonsecurity:S2083: a symlink in docs/kernels must not redirect the write."""
    outside = tmp_path / "outside.yaml"
    outside.write_text(TARGET, encoding="utf-8")
    root = _tree(tmp_path / "lib")
    link = root / "docs" / "kernels" / "R5" / "target.yaml"
    link.parent.mkdir(parents=True)
    link.symlink_to(outside)

    proc = _run(root, "--update-kernel", "target_kernel.v1", "--pass-rate", "0.92")

    assert proc.returncode != 0
    assert "outside" in proc.stdout + proc.stderr
    assert outside.read_text(encoding="utf-8") == TARGET
