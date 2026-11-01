"""Regression tests for scripts/refresh_retrieval_index.py (WU-34, F-058).

Deleting a canonical kernel file must be treated like canonical drift: the
refresher refuses ``--apply`` with a non-zero exit and keeps the entry, rather
than silently shrinking the kernel authority index. Directory entries are
reported, not a crash. All runs use copies in ``tmp_path``.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "refresh_retrieval_index.py"
SOUL = "docs/kernels/R0/soul_kernel.v1.yaml"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(repo / "scripts" / "refresh_retrieval_index.py"), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def _entry(sha: str, tags: list[str]) -> dict[str, Any]:
    return {"retrieval": "on_demand", "role": "context", "sha256": sha, "tags": tags}


def _synthetic_repo(root: Path) -> Path:
    (root / "scripts").mkdir(parents=True)
    shutil.copy2(SCRIPT, root / "scripts" / SCRIPT.name)
    (root / "docs" / "kernels" / "R5").mkdir(parents=True)
    kept_kernel = root / "docs/kernels/R5/kept.v1.yaml"
    kept_kernel.write_text("kernel_id: kept\n", encoding="utf-8")
    (root / "notes.md").write_text("changed\n", encoding="utf-8")
    (root / "adir").mkdir()
    files = {
        "AGENT_RETRIEVAL_INDEX.yaml": _entry("0" * 64, ["general"]),
        SOUL: _entry("a" * 64, ["kernels"]),  # canonical, file deleted
        "docs/kernels/R5/kept.v1.yaml": _entry(_sha(kept_kernel.read_bytes()), ["kernels"]),
        "notes.md": _entry("b" * 64, ["general"]),  # non-canonical drift
        "gone.md": _entry("c" * 64, ["general"]),  # non-canonical deletion
    }
    index = {"canonical_contract": "TransportPacket", "files": files}
    (root / "AGENT_RETRIEVAL_INDEX.yaml").write_text(
        yaml.safe_dump(index, sort_keys=False), encoding="utf-8"
    )
    return root


def test_deleted_canonical_kernel_refuses_apply_and_keeps_entry(tmp_path: Path) -> None:
    repo = _synthetic_repo(tmp_path / "repo")
    index_path = repo / "AGENT_RETRIEVAL_INDEX.yaml"
    before = index_path.read_bytes()

    proc = _run(repo, "--apply")

    assert proc.returncode != 0, proc.stdout
    assert index_path.read_bytes() == before, "index must not be rewritten"
    assert SOUL in yaml.safe_load(before)["files"]
    assert SOUL in proc.stdout + proc.stderr


def test_deleted_canonical_kernel_fails_check(tmp_path: Path) -> None:
    repo = _synthetic_repo(tmp_path / "repo")

    proc = _run(repo, "--check")

    assert proc.returncode != 0


def test_non_canonical_refresh_still_applies(tmp_path: Path) -> None:
    repo = _synthetic_repo(tmp_path / "repo")
    index_path = repo / "AGENT_RETRIEVAL_INDEX.yaml"
    # Restore the canonical kernel so only non-canonical changes remain.
    soul = repo / SOUL
    soul.parent.mkdir(parents=True)
    soul.write_text("kernel_id: soul\n", encoding="utf-8")
    index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    index["files"][SOUL]["sha256"] = _sha(soul.read_bytes())
    index_path.write_text(yaml.safe_dump(index, sort_keys=False), encoding="utf-8")

    proc = _run(repo, "--apply")

    assert proc.returncode == 0, proc.stdout + proc.stderr
    files = yaml.safe_load(index_path.read_text(encoding="utf-8"))["files"]
    assert "gone.md" not in files
    assert files["notes.md"]["sha256"] == _sha(b"changed\n")
    assert SOUL in files
    assert files["AGENT_RETRIEVAL_INDEX.yaml"]["sha256"] == "0" * 64  # self-entry untouched


def test_directory_entry_is_reported_not_crash(tmp_path: Path) -> None:
    repo = _synthetic_repo(tmp_path / "repo")
    index_path = repo / "AGENT_RETRIEVAL_INDEX.yaml"
    index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    index["files"]["adir"] = _entry("d" * 64, ["general"])
    index_path.write_text(yaml.safe_dump(index, sort_keys=False), encoding="utf-8")

    proc = _run(repo)

    assert "Traceback" not in proc.stderr, proc.stderr
    assert proc.returncode != 0
    assert "adir" in proc.stdout


def test_repository_copy_soul_kernel_deletion_is_refused(tmp_path: Path) -> None:
    """RG-58 on a git-archive copy of the committed tree."""
    archive = tmp_path / "head.tar"
    subprocess.run(
        ["git", "archive", "--format=tar", "-o", str(archive), "HEAD"], cwd=REPO_ROOT, check=True
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    with tarfile.open(archive) as tar:
        tar.extractall(repo, filter="data")
    # Exercise the working-tree refresher, not the committed one.
    shutil.copy2(SCRIPT, repo / "scripts" / SCRIPT.name)
    (repo / SOUL).unlink()
    index_path = repo / "AGENT_RETRIEVAL_INDEX.yaml"
    before = index_path.read_bytes()

    proc = _run(repo, "--apply")

    assert proc.returncode != 0
    assert index_path.read_bytes() == before
