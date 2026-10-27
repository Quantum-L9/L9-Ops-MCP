"""CI truthfulness regressions for .github/workflows/08-L11-CI-WORKFLOW-v3.3.yaml.

The step scripts are executed, not just inspected: each ``run:`` block is
rendered the way the Actions runner would render it (``${{ }}`` expressions
substituted textually from a known context; an unknown expression fails the
test) and run with the runner's default shell for Linux, ``bash -e {0}``.
Repositories are throwaway git repositories under ``tmp_path``; tools that
are not under test are replaced by recording stubs.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "08-L11-CI-WORKFLOW-v3.3.yaml"
GATE = REPO_ROOT / "scripts" / "validate-protected-files-v6.py"
VENV_BIN = Path(sys.executable).parent

EXPR = re.compile(r"\$\{\{\s*(.*?)\s*\}\}")

FIXTURE_POLICY = """\
version: "6.0.0"
enforcement_mode: fail_closed
categories:
  lcto_controlled:
    protected_paths:
      - Makefile
  subsystem_protected:
    subsystems: {}
approval_signals:
  pr_labels: [TEST_ONLY_APPROVAL_LABEL]
  commit_message_tokens: [TEST_ONLY_APPROVAL_TOKEN]
meta_protected_files: []
"""


# ── workflow harness ────────────────────────────────────────────────────


def _workflow() -> dict[str, Any]:
    return yaml.safe_load(WORKFLOW.read_text())


def _step(job: str, name: str) -> dict[str, Any]:
    for step in _workflow()["jobs"][job]["steps"]:
        if step.get("name") == name:
            return step
    raise AssertionError(f"step {name!r} not found in job {job!r}")


def _render(text: str, ctx: dict[str, str]) -> str:
    def sub(m: re.Match[str]) -> str:
        expr = m.group(1)
        if expr not in ctx:
            raise AssertionError(f"unrendered expression in workflow: {expr!r}")
        return ctx[expr]

    return EXPR.sub(sub, text)


def _read_outputs(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            out[key] = value
    return out


class Runner:
    """Executes workflow steps the way the hosted runner's default shell does."""

    def __init__(self, tmp: Path, workdir: Path, event: str = "pull_request") -> None:
        self.workdir = workdir
        self.temp = tmp / "runner_temp"
        self.temp.mkdir(exist_ok=True)
        self.stub_dir = tmp / "stubs"
        self.stub_dir.mkdir(exist_ok=True)
        self.cfg = tmp / "gitconfig"
        self.cfg.write_text(
            "[user]\n\tname = CI Test\n\temail = ci-test@example.invalid\n"
            "[commit]\n\tgpgsign = false\n"
            "[init]\n\tdefaultBranch = main\n"
        )
        self.ctx: dict[str, str] = {
            "github.event_name": event,
            "github.sha": "0" * 40,
            "github.actor": "ci-test",
            "steps.labels.outputs.labels": "",
        }
        self.n = 0

    def env(self) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env["GIT_CONFIG_GLOBAL"] = str(self.cfg)
        env["GIT_CONFIG_NOSYSTEM"] = "1"
        env["PATH"] = os.pathsep.join([str(self.stub_dir), str(VENV_BIN), env.get("PATH", "")])
        env["RUNNER_TEMP"] = str(self.temp)
        env["GITHUB_EVENT_NAME"] = self.ctx["github.event_name"]
        env["PR_LABELS"] = ""
        return env

    def stub(self, tool: str) -> Path:
        """Replace ``tool`` with a stub recording one argument per line."""
        log = self.stub_dir / f"{tool}.args"
        script = self.stub_dir / tool
        script.write_text(f"#!/usr/bin/env bash\nprintf '%s\\n' \"$@\" >> '{log}'\nexit 0\n")
        script.chmod(0o755)
        return log

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=self.workdir,
            env=self.env(),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    def run(self, job: str, name: str) -> subprocess.CompletedProcess[str]:
        step = _step(job, name)
        self.n += 1
        output_file = self.temp / f"output_{self.n}"
        output_file.touch()
        script = self.temp / f"step_{self.n}.sh"
        script.write_text(_render(step["run"], self.ctx))
        env = self.env()
        env["GITHUB_OUTPUT"] = str(output_file)
        for key, value in (step.get("env") or {}).items():
            env[key] = _render(str(value), self.ctx)
        proc = subprocess.run(
            ["bash", "-e", str(script)],
            cwd=self.workdir,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if step.get("id"):
            for key, value in _read_outputs(output_file).items():
                self.ctx[f"steps.{step['id']}.outputs.{key}"] = value
        return proc


def _init_repo(runner: Runner) -> None:
    runner.git("init", "-q", "-b", "main")
    (runner.workdir / "README.md").write_text("readme\n")
    runner.git("add", "README.md")
    runner.git("commit", "-q", "-m", "initial")


def _commit(runner: Runner, rel: str, text: str, message: str) -> None:
    path = runner.workdir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    runner.git("add", "--", rel)
    runner.git("commit", "-q", "-m", message)


def _set_ref(runner: Runner, ref: str, rev: str) -> None:
    runner.git("update-ref", ref, runner.git("rev-parse", rev))


# ── F-073: fast-test step must run tests ────────────────────────────────


def test_fast_test_step_fails_on_failing_test(tmp_path: Path) -> None:
    work = tmp_path / "work"
    (work / "tests").mkdir(parents=True)
    (work / "tests" / "test_injected.py").write_text(
        "def test_injected_failure():\n    assert False\n"
    )
    runner = Runner(tmp_path, work)
    proc = runner.run("lint-typecheck-test", "pytest (fast)")
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert "test_injected_failure" in proc.stdout + proc.stderr


# ── F-074: security and complexity scans must be able to fail ───────────


def test_bandit_step_fails_on_high_severity_finding(tmp_path: Path) -> None:
    work = tmp_path / "repo"
    work.mkdir()
    runner = Runner(tmp_path, work)
    _init_repo(runner)
    _set_ref(runner, "refs/remotes/origin/main", "main")
    runner.ctx["github.event.pull_request.base.sha"] = runner.git("rev-parse", "main")
    runner.git("switch", "-q", "-c", "feature")
    _commit(
        runner,
        "src/insecure.py",
        "import requests\n\nrequests.get('https://example.invalid', verify=False, timeout=5)\n",
        "add insecure call",
    )
    assert runner.run("lint-typecheck-test", "Get Changed Files").returncode == 0
    proc = runner.run("lint-typecheck-test", "Bandit Security Scan")
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert (work / "bandit-report.json").exists()


COMPLEX_FN = (
    "def branchy(x):\n"
    + "".join(f"    if x == {i}:\n        return {i}\n" for i in range(12))
    + "    return -1\n"
)


def test_complexity_step_fails_above_threshold(tmp_path: Path) -> None:
    work = tmp_path / "work"
    (work / "src").mkdir(parents=True)
    (work / "scripts").mkdir()
    (work / "src" / "complex_mod.py").write_text(COMPLEX_FN)
    runner = Runner(tmp_path, work)
    proc = runner.run("lint-typecheck-test", "Complexity Check")
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert "branchy" in proc.stdout


def test_complexity_step_passes_simple_code(tmp_path: Path) -> None:
    work = tmp_path / "work"
    (work / "src").mkdir(parents=True)
    (work / "scripts").mkdir()
    (work / "src" / "simple_mod.py").write_text("def simple(x):\n    return x + 1\n")
    runner = Runner(tmp_path, work)
    proc = runner.run("lint-typecheck-test", "Complexity Check")
    assert proc.returncode == 0, proc.stdout + proc.stderr


# ── F-075: PR file names are data, not shell text ───────────────────────


def test_file_name_with_shell_metacharacters_is_not_executed(tmp_path: Path) -> None:
    work = tmp_path / "repo"
    work.mkdir()
    runner = Runner(tmp_path, work)
    _init_repo(runner)
    _set_ref(runner, "refs/remotes/origin/main", "main")
    runner.ctx["github.event.pull_request.base.sha"] = runner.git("rev-parse", "main")
    runner.git("switch", "-q", "-c", "feature")
    evil = "x$(touch PWNED).py"
    _commit(runner, evil, "X = 1\n", "add file")
    ruff_log = runner.stub("ruff")

    assert runner.run("lint-typecheck-test", "Get Changed Files").returncode == 0
    lint = runner.run("lint-typecheck-test", "Ruff Lint")
    fmt = runner.run("lint-typecheck-test", "Ruff Format Check")

    assert not (work / "PWNED").exists(), "file name was executed as shell code"
    assert lint.returncode == 0, lint.stdout + lint.stderr
    assert fmt.returncode == 0, fmt.stdout + fmt.stderr
    assert ruff_log.read_text().splitlines().count(evil) == 2


# ── F-054: diff against the PR's real base ──────────────────────────────


def _develop_pr_repo(runner: Runner) -> None:
    """main <- develop (adds dev_only.py, edits Makefile) <- feature (adds feat.py)."""
    _init_repo(runner)
    _commit(runner, "Makefile", "all:\n\t@true\n", "makefile")
    _set_ref(runner, "refs/remotes/origin/main", "main")
    runner.git("switch", "-q", "-c", "develop")
    _commit(runner, "dev_only.py", "D = 1\n", "develop-only module")
    _commit(runner, "Makefile", "all:\n\t@echo develop\n", "develop edits makefile")
    _set_ref(runner, "refs/remotes/origin/develop", "develop")
    runner.ctx["github.event.pull_request.base.sha"] = runner.git("rev-parse", "develop")
    runner.git("switch", "-q", "-c", "feature")
    _commit(runner, "feat.py", "F = 1\n", "feature module")


def test_lint_diffs_against_pr_base(tmp_path: Path) -> None:
    work = tmp_path / "repo"
    work.mkdir()
    runner = Runner(tmp_path, work)
    _develop_pr_repo(runner)
    ruff_log = runner.stub("ruff")

    assert runner.run("lint-typecheck-test", "Get Changed Files").returncode == 0
    proc = runner.run("lint-typecheck-test", "Ruff Lint")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    args = ruff_log.read_text().splitlines()
    assert "feat.py" in args
    assert "dev_only.py" not in args


def test_protected_files_gate_diffs_against_pr_base(tmp_path: Path) -> None:
    work = tmp_path / "repo"
    work.mkdir()
    runner = Runner(tmp_path, work)
    (work / "scripts").mkdir()
    shutil.copy(GATE, work / "scripts" / GATE.name)
    (work / "config" / "policies").mkdir(parents=True)
    (work / "config" / "policies" / "protected_files.yaml").write_text(FIXTURE_POLICY)
    (work / ".gitignore").write_text("scripts/\nconfig/\nprotected_files_gate_report.json\n")
    _develop_pr_repo(runner)

    # The PR (feature -> develop) does not touch Makefile; develop did.
    proc = runner.run("protected-files", "Validate Protected Files")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert '"reason": "no_violations"' in (work / "protected_files_gate_report.json").read_text()


# ── Step-level invariants for the jobs WU-29 repairs ────────────────────


@pytest.mark.parametrize("job", ["lint-typecheck-test", "protected-files"])
def test_check_steps_cannot_swallow_failures(job: str) -> None:
    spec = _workflow()["jobs"][job]
    assert "continue-on-error" not in spec
    for step in spec["steps"]:
        assert "continue-on-error" not in step, step["name"]
        run = step.get("run", "")
        assert "|| true" not in run, step["name"]
        assert "${{" not in run, f"expression interpolated into run: {step['name']}"


def test_merge_gate_needs_existing_jobs() -> None:
    jobs = _workflow()["jobs"]
    needs = jobs["merge-gate"]["needs"]
    assert set(needs) <= set(jobs)
    script = jobs["merge-gate"]["steps"][0]["run"]
    for need in needs:
        assert f"needs.{need}.result" in script, need
