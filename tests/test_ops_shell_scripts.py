"""Regression tests for install/preflight/library-health shell scripts (WU-43).

F-083: ``.env`` values were sourced without export, so child processes (the
config writers, Python checks) silently used defaults; the Neo4j wait used
``grep -q healthy`` which also matches ``(unhealthy)``.
F-084: ``library_health_v341.sh`` aborted after its first header under
``set -e`` and used the invalid ``tr -n``.

The scripts run from copies in ``tmp_path`` with stub ``docker``/``python``/
``pip``/``sleep`` commands first on ``PATH``; nothing real is started.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash is required")

STUB_DOCKER = """#!/usr/bin/env bash
# docker stub: compose up/ps and inspect, health taken from $STUB_HEALTH.
echo "docker $*" >> "$STUB_LOG"
if [ "$1" = "compose" ]; then
  shift
  while [ "$#" -gt 0 ] && [ "$1" != "up" ] && [ "$1" != "ps" ]; do shift; done
  case "$1" in
    up) exit 0 ;;
    ps)
      if [ "${2:-}" = "-q" ] || [ "${2:-}" = "--quiet" ]; then echo "cid-neo4j"; exit 0; fi
      echo "NAME      IMAGE   STATUS"
      echo "l9-neo4j  neo4j   Up 5 seconds (${STUB_HEALTH})"
      exit 0 ;;
  esac
fi
if [ "$1" = "inspect" ]; then echo "$STUB_HEALTH"; exit 0; fi
exit 0
"""

# Records the env each python invocation sees; fails the cursor writer on demand.
STUB_PYTHON = """#!/usr/bin/env bash
echo "python $* | L9_NEO4J_PASS=${L9_NEO4J_PASS:-<unset>}" >> "$STUB_LOG"
case "$*" in
  *write_cursor_config.py*) exit "${STUB_CURSOR_WRITER_RC:-0}" ;;
  *l9_ops_mcp.seed*) exit "${STUB_SEED_RC:-0}" ;;
esac
cat > /dev/null 2>&1 || true
exit 0
"""

STUB_OK = "#!/usr/bin/env bash\nexit 0\n"


def _stub_bin(root: Path) -> Path:
    bindir = root / "stubbin"
    bindir.mkdir()
    for name, body in {
        "docker": STUB_DOCKER,
        "python": STUB_PYTHON,
        "pip": STUB_OK,
        "sleep": STUB_OK,
    }.items():
        path = bindir / name
        path.write_text(body, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return bindir


def _repo_copy(root: Path, *scripts: str) -> Path:
    repo = root / "repo"
    (repo / "scripts").mkdir(parents=True)
    for name in scripts:
        shutil.copy2(SCRIPTS / name, repo / "scripts" / name)
    return repo


def _env(root: Path, bindir: Path, **extra: str) -> dict[str, str]:
    env = {
        "PATH": f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}",
        "HOME": str(root / "home"),
        "STUB_LOG": str(root / "stub.log"),
    }
    env.update(extra)
    return env


def _bash(script: Path, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(script)],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


@pytest.mark.parametrize("script", ["install.sh", "preflight.sh"])
def test_dotenv_values_reach_child_processes(tmp_path: Path, script: str) -> None:
    repo = _repo_copy(tmp_path, script)
    (repo / ".env").write_text("L9_NEO4J_PASS=CHANGED\n", encoding="utf-8")
    (tmp_path / "home").mkdir()
    bindir = _stub_bin(tmp_path)

    proc = _bash(repo / "scripts" / script, repo, _env(tmp_path, bindir, STUB_HEALTH="healthy"))

    log = (tmp_path / "stub.log").read_text(encoding="utf-8")
    python_calls = [line for line in log.splitlines() if line.startswith("python ")]
    assert python_calls, proc.stdout + proc.stderr
    assert all(line.endswith("L9_NEO4J_PASS=CHANGED") for line in python_calls), log


def test_install_defaults_apply_when_dotenv_absent(tmp_path: Path) -> None:
    repo = _repo_copy(tmp_path, "install.sh")
    (tmp_path / "home").mkdir()
    bindir = _stub_bin(tmp_path)

    proc = _bash(
        repo / "scripts" / "install.sh", repo, _env(tmp_path, bindir, STUB_HEALTH="healthy")
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_install_rejects_unhealthy_neo4j(tmp_path: Path) -> None:
    repo = _repo_copy(tmp_path, "install.sh")
    (tmp_path / "home").mkdir()
    bindir = _stub_bin(tmp_path)

    proc = _bash(
        repo / "scripts" / "install.sh", repo, _env(tmp_path, bindir, STUB_HEALTH="unhealthy")
    )

    assert proc.returncode != 0
    assert "did not become healthy" in proc.stdout + proc.stderr
    log = (tmp_path / "stub.log").read_text(encoding="utf-8")
    assert "Installing Python package" not in proc.stdout
    assert not any(line.startswith("python ") for line in log.splitlines())


def test_install_continues_when_a_config_writer_refuses(tmp_path: Path) -> None:
    repo = _repo_copy(tmp_path, "install.sh")
    (tmp_path / "home").mkdir()
    bindir = _stub_bin(tmp_path)
    env = _env(tmp_path, bindir, STUB_HEALTH="healthy", STUB_CURSOR_WRITER_RC="1")

    proc = _bash(repo / "scripts" / "install.sh", repo, env)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Cursor MCP config NOT written" in proc.stdout
    assert "Install complete" in proc.stdout


def _health_tree(root: Path) -> Path:
    repo = _repo_copy(root, "library_health_v341.sh")
    for name in ("alpha", "beta", "gamma"):
        skill = repo / "skills" / name / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(f"# {name}\n", encoding="utf-8")  # no last_tested
    kernel = repo / "docs" / "kernels" / "R5" / "k.v1.yaml"
    kernel.parent.mkdir(parents=True)
    kernel.write_text("kernel_id: k.v1\nring: R5\npurpose: Governs.\n", encoding="utf-8")
    return repo


def test_library_health_reports_every_item_and_fails(tmp_path: Path) -> None:
    repo = _health_tree(tmp_path)

    proc = _bash(repo / "scripts" / "library_health_v341.sh", repo, dict(os.environ))

    out = proc.stdout + proc.stderr
    for name in ("alpha", "beta", "gamma"):
        assert f"skills/{name}/SKILL.md" in out, out
    assert "missing changes_from_v3.3.0" in out
    assert "missing trust_ladder_kernel.v1" in out
    assert "tr:" not in out, out
    assert proc.returncode != 0, "a FAIL item must produce a non-zero exit"


def test_library_health_clean_tree_exits_zero(tmp_path: Path) -> None:
    repo = _repo_copy(tmp_path, "library_health_v341.sh")
    skill = repo / "skills" / "alpha" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nlast_tested: 2026-10-01\n---\n# alpha\n", encoding="utf-8")
    kernel = repo / "docs" / "kernels" / "R5" / "k.v1.yaml"
    kernel.parent.mkdir(parents=True)
    kernel.write_text(
        "kernel_id: k.v1\nring: R5\nchanges_from_v3.3.0: []\n"
        "requires: [trust_ladder_kernel.v1]\n"
        "purpose: >\n  Use WHEN budgets apply BECAUSE limits exist.\n",
        encoding="utf-8",
    )

    proc = _bash(repo / "scripts" / "library_health_v341.sh", repo, dict(os.environ))

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "FAIL:" not in proc.stdout


@pytest.mark.parametrize("present", [(), ("kernels",), ("skills",)])
def test_library_health_missing_or_empty_input_fails(
    tmp_path: Path, present: tuple[str, ...]
) -> None:
    """F-pr38-10: with nothing to check the script printed '0 failures' and exited 0."""
    repo = _repo_copy(tmp_path, "library_health_v341.sh")
    (repo / "skills").mkdir()  # an empty directory is as empty as a missing one
    if "kernels" in present:
        kernel = repo / "docs" / "kernels" / "R5" / "k.v1.yaml"
        kernel.parent.mkdir(parents=True)
        kernel.write_text("kernel_id: k.v1\nchanges_from_v3.3.0: []\n", encoding="utf-8")
    if "skills" in present:
        skill = repo / "skills" / "alpha" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nlast_tested: 2026-10-01\n---\n", encoding="utf-8")

    proc = _bash(repo / "scripts" / "library_health_v341.sh", repo, dict(os.environ))

    assert proc.returncode != 0, proc.stdout
    assert "NO INPUT" in proc.stdout


@pytest.mark.parametrize(
    ("seed_rc", "expected"),
    [
        ("2", "seed skipped (CANONICAL_LAW.md not found"),
        ("1", "seed failed (exit 1)"),
    ],
)
def test_install_reports_seed_outcome_by_exit_code(
    tmp_path: Path, seed_rc: str, expected: str
) -> None:
    """A rejected or failed seed is not reported as a missing CANONICAL_LAW.md (WU-11)."""
    repo = _repo_copy(tmp_path, "install.sh")
    (tmp_path / "home").mkdir()
    bindir = _stub_bin(tmp_path)
    env = _env(tmp_path, bindir, STUB_HEALTH="healthy", STUB_SEED_RC=seed_rc)

    proc = _bash(repo / "scripts" / "install.sh", repo, env)
    output = proc.stdout + proc.stderr

    assert expected in output
    other = "seed failed" if seed_rc == "2" else "seed skipped"
    assert other not in output
    if seed_rc == "2":
        # Missing input is a documented skip: the install still completes.
        assert proc.returncode == 0, output
        assert "Install complete" in proc.stdout
    else:
        # A rejected chunk or failed write is a failed install (PR #38 review).
        assert proc.returncode == int(seed_rc), output
        assert "Install complete" not in proc.stdout


def test_preflight_group_ids_pass_graphiti_validation() -> None:
    """Every group_id literal preflight.sh sends must be accepted by graphiti-core (WU-01)."""
    import re

    from graphiti_core.helpers import validate_group_id

    text = (REPO_ROOT / "scripts" / "preflight.sh").read_text(encoding="utf-8")
    group_ids = re.findall(r'group_ids?=\[?"([^"]+)"', text)
    assert group_ids, "preflight.sh no longer sends a group_id literal"
    for group_id in group_ids:
        validate_group_id(group_id)
