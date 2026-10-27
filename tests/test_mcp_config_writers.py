"""Regression tests for the MCP client config writers (WU-38: F-064, F-065).

``scripts/write_cursor_config.py`` and ``scripts/write_claude_config.py`` merge
the ``l9-ops-mcp`` entry into a user's existing client config. They must never
destroy the user's other servers (an unparseable or unexpected-shape config is
left byte-for-byte untouched and the writer exits non-zero naming the file),
and the written file carries credentials, so it must be mode 0600 and replaced
atomically.

Every test sets ``HOME`` to ``tmp_path``; no real user config is touched.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

WRITERS = {
    "cursor": (REPO_ROOT / "scripts" / "write_cursor_config.py", Path(".cursor/mcp.json")),
    "claude": (
        REPO_ROOT / "scripts" / "write_claude_config.py",
        Path(".config/Claude/claude_desktop_config.json"),
    ),
}

pytestmark = pytest.mark.skipif(
    sys.platform != "linux",
    reason="claude writer resolves its config path per platform; paths here are the Linux ones",
)

OTHER_SERVER = {"command": "node", "args": ["other.js"]}
ENV_OVERRIDES = {
    "L9_NEO4J_URI": "bolt://db.example:7687",
    "L9_NEO4J_USER": "svc",
    "L9_NEO4J_PASS": "s3cret-not-default",
    "L9_OPENAI_API_KEY": "sk-test-placeholder",
}


def _run(script: Path, home: Path) -> subprocess.CompletedProcess[str]:
    env = {"PATH": os.environ.get("PATH", ""), "HOME": str(home), **ENV_OVERRIDES}
    return subprocess.run(
        [sys.executable, str(script)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
        preexec_fn=lambda: os.umask(0o022),
    )


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


@pytest.fixture(params=sorted(WRITERS))
def writer(request: pytest.FixtureRequest, tmp_path: Path) -> tuple[Path, Path, Path]:
    script, rel_cfg = WRITERS[request.param]
    home = tmp_path / "home"
    home.mkdir()
    return script, home, home / rel_cfg


@pytest.mark.parametrize(
    "existing",
    [
        # JSONC: comments and a trailing comma (what Cursor/VS Code users write).
        '{\n  // my servers\n  "mcpServers": {\n    "other": {"command": "node"},\n  }\n}\n',
        '{"mcpServers": null}\n',
        '[{"mcpServers": {}}]\n',
        '{"mcpServers": ["other"]}\n',
    ],
    ids=["jsonc", "servers-null", "top-level-list", "servers-list"],
)
def test_unusable_config_is_left_untouched_and_refused(
    writer: tuple[Path, Path, Path], existing: str
) -> None:
    script, home, cfg = writer
    cfg.parent.mkdir(parents=True)
    cfg.write_text(existing, encoding="utf-8")

    proc = _run(script, home)

    assert proc.returncode != 0
    assert cfg.read_text(encoding="utf-8") == existing
    assert str(cfg) in proc.stderr, f"refusal must name the file: {proc.stderr!r}"
    assert "Traceback" not in proc.stderr
    assert list(cfg.parent.iterdir()) == [cfg], "no stray temp files"


def test_merge_preserves_other_servers_and_writes_0600(writer: tuple[Path, Path, Path]) -> None:
    script, home, cfg = writer
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        json.dumps({"theme": "dark", "mcpServers": {"other": OTHER_SERVER}}), encoding="utf-8"
    )
    cfg.chmod(0o644)

    proc = _run(script, home)

    assert proc.returncode == 0, proc.stderr
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["theme"] == "dark"
    assert data["mcpServers"]["other"] == OTHER_SERVER
    entry = data["mcpServers"]["l9-ops-mcp"]
    assert entry["args"] == ["-m", "l9_ops_mcp.server"]
    assert entry["env"]["L9_NEO4J_PASS"] == ENV_OVERRIDES["L9_NEO4J_PASS"]
    assert entry["env"]["L9_NEO4J_URI"] == ENV_OVERRIDES["L9_NEO4J_URI"]
    assert _mode(cfg) == 0o600
    assert list(cfg.parent.iterdir()) == [cfg], "no stray temp files"


def test_new_config_is_created_0600(writer: tuple[Path, Path, Path]) -> None:
    script, home, cfg = writer

    proc = _run(script, home)

    assert proc.returncode == 0, proc.stderr
    assert _mode(cfg) == 0o600
    assert "l9-ops-mcp" in json.loads(cfg.read_text(encoding="utf-8"))["mcpServers"]


def test_rerun_is_idempotent(writer: tuple[Path, Path, Path]) -> None:
    script, home, cfg = writer

    assert _run(script, home).returncode == 0
    first = cfg.read_bytes()
    assert _run(script, home).returncode == 0
    assert cfg.read_bytes() == first
