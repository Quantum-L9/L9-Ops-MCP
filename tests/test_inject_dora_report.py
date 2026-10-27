"""Regression tests for scripts/inject_dora_complete.py (WU-44, decision D-18 A).

The injector's mutating modes (--execute, --force) corrupted Python files and
reported success. Under D-18 A the script is a read-only report: it must never
write a scanned file, its counts must be truthful, and any per-file failure must
produce a non-zero exit. CI calls it as ``--repo . --dry-run --report <path>``.

Every test runs against a copy in ``tmp_path``; the repository is never mutated.
"""

from __future__ import annotations

import hashlib
import json
import py_compile
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "inject_dora_complete.py"

# Constructs the former --execute mode broke (F-040, F-041, F-043).
FIXTURE_FILES: dict[str, bytes] = {
    "pkg/banner.py": b"# Copyright banner\n# second line\n'''Doc.'''\nX = 1\n",
    "pkg/future_multi.py": (
        b"from __future__ import (\n    annotations,\n)\n\n\ndef f() -> int:\n    return 1\n"
    ),
    "pkg/bom.py": b'\xef\xbb\xbf"""Doc with BOM."""\nY = 2\n',
    "pkg/empty_doc.py": b'""""""\nS = """keep\nthis"""\n',
    "pkg/quoted.py": b'"""Says "hi" and \\u00e9 \\\\ backslash."""\nZ = 3\n',
    "pkg/has_all.py": (b"__dora_meta__ = {}\nV = 1\n__dora_footer__ = {}\n__l9_trace__ = {}\n"),
    "config/settings.yaml": b"key: value\n",
    "config/tagged.yaml": b"# DORA META\n# DORA FOOTER\nkey: value\n",
    ".github/workflows/ci.yml": b"name: ci\non: push\n",
}


def _build_tree(root: Path, files: dict[str, bytes]) -> None:
    for rel, data in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def _digest_tree(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )


def _git_archive_copy(dest: Path) -> Path:
    """Export the committed tree (``git archive HEAD``) into ``dest``."""
    archive = dest / "head.tar"
    subprocess.run(
        ["git", "archive", "--format=tar", "-o", str(archive), "HEAD"],
        cwd=REPO_ROOT,
        check=True,
    )
    tree = dest / "repo"
    tree.mkdir()
    with tarfile.open(archive) as tar:
        tar.extractall(tree, filter="data")
    archive.unlink()
    return tree


@pytest.mark.parametrize(
    "mode", [["--execute"], ["--execute", "--force"], ["--dry-run", "--force"]]
)
def test_former_mutating_modes_write_nothing(tmp_path: Path, mode: list[str]) -> None:
    repo = tmp_path / "repo"
    _build_tree(repo, FIXTURE_FILES)
    before = _digest_tree(repo)

    proc = _run("--repo", str(repo), *mode, "--report", str(tmp_path / "r.json"), cwd=tmp_path)

    assert proc.returncode != 0, "a removed mutating mode must be refused"
    assert _digest_tree(repo) == before, "no scanned file may be modified"


def test_execute_scenario_on_repository_copy_leaves_every_file_compiling(tmp_path: Path) -> None:
    """RG-40: the audit's --execute run on a git-archive copy broke 34 files."""
    repo = _git_archive_copy(tmp_path)
    before = _digest_tree(repo)

    proc = _run(
        "--repo", str(repo), "--execute", "--report", str(tmp_path / "r.json"), cwd=tmp_path
    )

    assert proc.returncode != 0
    assert _digest_tree(repo) == before
    for py in sorted(repo.rglob("*.py")):
        py_compile.compile(str(py), cfile=str(tmp_path / "c.pyc"), doraise=True)


def test_dry_run_report_counts_are_truthful_and_read_only(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _build_tree(repo, FIXTURE_FILES)
    before = _digest_tree(repo)
    report_path = tmp_path / "report.json"

    proc = _run("--repo", str(repo), "--dry-run", "--report", str(report_path), cwd=tmp_path)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _digest_tree(repo) == before
    report = json.loads(report_path.read_text(encoding="utf-8"))

    py_missing = {"pkg/banner.py", "pkg/future_multi.py", "pkg/bom.py"}
    py_missing |= {"pkg/empty_doc.py", "pkg/quoted.py"}
    yaml_missing = {"config/settings.yaml", ".github/workflows/ci.yml"}

    assert report["total_files"] == len(FIXTURE_FILES)
    assert report["failed"] == 0
    # Python files lacking each block, plus YAML files lacking header/footer.
    assert report["header_injected"] == len(py_missing) + len(yaml_missing)
    assert report["footer_injected"] == len(py_missing) + len(yaml_missing)
    # YAML has no trace block: only Python files count (F-048).
    assert report["trace_injected"] == len(py_missing)
    assert report["skipped"] == 2  # pkg/has_all.py and config/tagged.yaml
    listed = {Path(entry["file"]).relative_to(repo).as_posix() for entry in report["files"]}
    # .github is not excluded by a '.git' substring match (F-049).
    assert ".github/workflows/ci.yml" in listed


def test_repo_path_containing_skip_word_is_still_scanned(tmp_path: Path) -> None:
    """F-049: a --repo path that merely contains 'tests' excluded every file."""
    repo = tmp_path / "mytests_deploy_repo"
    _build_tree(repo, {"pkg/a.py": b"A = 1\n", "tests/test_a.py": b"B = 1\n"})
    report_path = tmp_path / "report.json"

    proc = _run("--repo", str(repo), "--dry-run", "--report", str(report_path), cwd=tmp_path)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    listed = {Path(entry["file"]).relative_to(repo).as_posix() for entry in report["files"]}
    assert listed == {"pkg/a.py"}  # tests/ directory still excluded by component


def test_relative_repo_path_is_supported(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _build_tree(repo, {"pkg/a.py": b"A = 1\n"})
    report_path = tmp_path / "report.json"

    proc = _run("--repo", "repo", "--dry-run", "--report", str(report_path), cwd=tmp_path)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["total_files"] == 1
    assert report["files"][0]["component_id"].startswith("PKG-")


@pytest.mark.parametrize(
    ("name", "data"),
    [("pkg/broken.py", b"def f(:\n"), ("pkg/undecodable.py", b"X = '\xff\xfe'\n")],
)
def test_per_file_failure_is_counted_and_exits_non_zero(
    tmp_path: Path, name: str, data: bytes
) -> None:
    """F-042: failures were counted as skipped and the run exited 0."""
    repo = tmp_path / "repo"
    _build_tree(repo, {"pkg/ok.py": b"A = 1\n", name: data})
    report_path = tmp_path / "report.json"

    proc = _run("--repo", str(repo), "--dry-run", "--report", str(report_path), cwd=tmp_path)

    assert proc.returncode != 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["failed"] == 1
    assert report["skipped"] == 0
    assert [Path(f["file"]).name for f in report["failures"]] == [Path(name).name]


def test_summary_output_interpolates_counts(tmp_path: Path) -> None:
    """F-048: the summary printed literal '{results[...]}' placeholders."""
    repo = tmp_path / "repo"
    _build_tree(repo, {"pkg/a.py": b"A = 1\n"})

    proc = _run("--repo", str(repo), "--report", str(tmp_path / "r.json"), cwd=tmp_path)

    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert "{results" not in out
    assert "total files: 1" in out


def test_no_files_found_exits_non_zero(tmp_path: Path) -> None:
    repo = tmp_path / "empty"
    repo.mkdir()

    proc = _run(
        "--repo", str(repo), "--dry-run", "--report", str(tmp_path / "r.json"), cwd=tmp_path
    )

    assert proc.returncode != 0
