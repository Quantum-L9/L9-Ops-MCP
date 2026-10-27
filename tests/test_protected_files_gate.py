"""Regression tests for the protected-files gate (scripts/validate-protected-files-v6.py).

Every scenario runs the real gate as a subprocess inside a throwaway git
repository, so the gate's own git invocations are exercised end to end.

The fixture policy uses test-only approval signals so that no real approval
token appears in this repository's files or commits.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "validate-protected-files-v6.py"
REPORT = "protected_files_gate_report.json"

TEST_TOKEN = "TEST_ONLY_APPROVAL_TOKEN"
TEST_LABEL = "TEST_ONLY_APPROVAL_LABEL"

FIXTURE_POLICY = f"""\
version: "6.0.0"
enforcement_mode: fail_closed
categories:
  lcto_controlled:
    approval_required: true
    protected_paths:
      - Makefile
  subsystem_protected:
    subsystems: {{}}
approval_signals:
  pr_labels:
    - {TEST_LABEL}
  commit_message_tokens:
    - {TEST_TOKEN}
meta_protected_files: []
"""


def _git_env(home: Path) -> dict[str, str]:
    """Isolate git from the developer's global/system config (signing, hooks)."""
    cfg = home / "gitconfig"
    if not cfg.exists():
        cfg.write_text(
            "[user]\n\tname = Gate Test\n\temail = gate-test@example.invalid\n"
            "[commit]\n\tgpgsign = false\n"
            "[init]\n\tdefaultBranch = main\n"
        )
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_CONFIG_GLOBAL"] = str(cfg)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["PR_LABELS"] = ""
    return env


class Repo:
    def __init__(self, root: Path, home: Path) -> None:
        self.root = root
        self.env = _git_env(home)

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def commit(self, message: str, *paths: str) -> None:
        self.git("add", "--", *paths)
        self.git("commit", "-q", "-m", message)

    def run_gate(self, *args: str, labels: str = "") -> tuple[int, dict]:
        env = dict(self.env)
        env["PR_LABELS"] = labels
        report = self.root / REPORT
        if report.exists():
            report.unlink()
        proc = subprocess.run(
            [sys.executable, str(GATE), *args],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        data = json.loads(report.read_text()) if report.exists() else {}
        return proc.returncode, data


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    root = tmp_path / "repo"
    root.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    r = Repo(root, home)
    r.git("init", "-q", "-b", "main")
    r.write("config/policies/protected_files.yaml", FIXTURE_POLICY)
    r.write("Makefile", "all:\n\t@true\n")
    r.write("README.md", "readme\n")
    r.commit("initial", "config/policies/protected_files.yaml", "Makefile", "README.md")
    return r


def _publish_main(repo: Repo) -> None:
    """Make refs/remotes/origin/main point at the local main tip."""
    repo.git("update-ref", "refs/remotes/origin/main", repo.git("rev-parse", "main"))


# ── F-050: change set cannot be computed ────────────────────────────────


def test_missing_base_ref_fails_closed(repo: Repo) -> None:
    repo.git("switch", "-q", "-c", "feature")
    repo.write("Makefile", "all:\n\t@echo changed\n")
    repo.commit("edit protected file", "Makefile")
    # No refs/remotes/origin/main exists: the change set is not computable.
    code, report = repo.run_gate()
    assert code == 1, report
    assert report["passed"] is False
    assert report["reason"] == "change_set_unavailable"
    assert "origin/main" in report.get("error", "")


def test_missing_base_ref_fails_closed_even_in_dry_run(repo: Repo) -> None:
    repo.git("switch", "-q", "-c", "feature")
    code, report = repo.run_gate("--dry-run")
    assert code == 1, report
    assert report["reason"] == "change_set_unavailable"


# ── F-051: approvals only from the PR's own commits ─────────────────────


def test_token_on_base_only_commit_does_not_approve(repo: Repo) -> None:
    _publish_main(repo)
    repo.git("switch", "-q", "-c", "feature")
    repo.write("Makefile", "all:\n\t@echo changed\n")
    repo.commit("edit protected file", "Makefile")
    repo.git("switch", "-q", "main")
    repo.write("README.md", "docs only\n")
    repo.commit(f"docs: update readme {TEST_TOKEN}", "README.md")
    _publish_main(repo)
    repo.git("switch", "-q", "feature")

    code, report = repo.run_gate()
    assert code == 1, report
    assert report["reason"] == "blocked"
    assert [v["file"] for v in report["violations"]] == ["Makefile"]


def test_token_in_pr_commit_approves(repo: Repo) -> None:
    _publish_main(repo)
    repo.git("switch", "-q", "-c", "feature")
    repo.write("Makefile", "all:\n\t@echo changed\n")
    repo.commit(f"edit protected file {TEST_TOKEN}", "Makefile")
    code, report = repo.run_gate()
    assert code == 0, report
    assert report["reason"] == "approved"


def test_label_approves(repo: Repo) -> None:
    _publish_main(repo)
    repo.git("switch", "-q", "-c", "feature")
    repo.write("Makefile", "all:\n\t@echo changed\n")
    repo.commit("edit protected file", "Makefile")
    code, report = repo.run_gate(labels=f"bug,{TEST_LABEL}")
    assert code == 0, report
    assert report["reason"] == "approved"


# ── F-052: renaming a protected file away ───────────────────────────────


def test_rename_of_protected_file_is_detected(repo: Repo) -> None:
    _publish_main(repo)
    repo.git("switch", "-q", "-c", "feature")
    repo.git("mv", "Makefile", "Makefile.old")
    repo.git("commit", "-q", "-m", "rename")
    code, report = repo.run_gate()
    assert code == 1, report
    assert "Makefile" in [v["file"] for v in report["violations"]]


def test_deletion_of_protected_file_is_detected(repo: Repo) -> None:
    _publish_main(repo)
    repo.git("switch", "-q", "-c", "feature")
    repo.git("rm", "-q", "Makefile")
    repo.git("commit", "-q", "-m", "delete")
    code, report = repo.run_gate()
    assert code == 1, report
    assert [v["file"] for v in report["violations"]] == ["Makefile"]


# ── Preserved behaviour ─────────────────────────────────────────────────


def test_unprotected_change_passes(repo: Repo) -> None:
    _publish_main(repo)
    repo.git("switch", "-q", "-c", "feature")
    repo.write("README.md", "changed\n")
    repo.commit("docs", "README.md")
    code, report = repo.run_gate()
    assert code == 0, report
    assert report["reason"] == "no_violations"


def test_empty_change_set_passes(repo: Repo) -> None:
    _publish_main(repo)
    repo.git("switch", "-q", "-c", "feature")
    code, report = repo.run_gate()
    assert code == 0, report
    assert report["reason"] == "no_changes"
