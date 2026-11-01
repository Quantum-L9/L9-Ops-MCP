"""MCP server transport startup (RG-09)."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx
import pytest

import l9_ops_mcp.server as server

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def restore_settings():
    s = server.mcp.settings
    saved = (s.host, s.port, s.streamable_http_path, s.transport_security)
    yield
    s.host, s.port, s.streamable_http_path, s.transport_security = saved


def test_http_mode_configures_settings_and_runs_streamable_http(monkeypatch, restore_settings):
    calls: list[tuple[str, int, str]] = []

    async def fake_run() -> None:
        s = server.mcp.settings
        calls.append((s.host, s.port, s.streamable_http_path))

    monkeypatch.setattr(server.mcp, "run_streamable_http_async", fake_run)
    monkeypatch.setenv("L9_MCP_TRANSPORT", "http")
    monkeypatch.setenv("L9_MCP_HTTP_HOST", "127.0.0.1")
    monkeypatch.setenv("L9_MCP_HTTP_PORT", "7999")
    server.main()
    assert calls == [("127.0.0.1", 7999, "/mcp")]


def test_stdio_remains_default(monkeypatch):
    calls: list[str] = []

    async def fake_stdio() -> None:
        calls.append("stdio")

    monkeypatch.setattr(server.mcp, "run_stdio_async", fake_stdio)
    monkeypatch.delenv("L9_MCP_TRANSPORT", raising=False)
    server.main()
    assert calls == ["stdio"]


def test_invalid_port_is_a_clear_error(monkeypatch, restore_settings):
    monkeypatch.setenv("L9_MCP_TRANSPORT", "http")
    monkeypatch.setenv("L9_MCP_HTTP_PORT", "not-a-port")
    with pytest.raises(SystemExit) as exc:
        server.main()
    assert exc.value.code not in (0, None)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _initialize(url: str) -> httpx.Response:
    body: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "rg09", "version": "0"},
        },
    }
    return httpx.post(
        url,
        json=body,
        headers={"Accept": "application/json, text/event-stream"},
        timeout=5.0,
    )


def test_http_server_answers_initialize():
    port = _free_port()
    env = {
        **os.environ,
        "L9_MCP_TRANSPORT": "http",
        "L9_MCP_HTTP_HOST": "127.0.0.1",
        "L9_MCP_HTTP_PORT": str(port),
        "PYTHONPATH": str(REPO_ROOT / "src"),
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "l9_ops_mcp.server"],
        env=env,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        url = f"http://127.0.0.1:{port}/mcp"
        deadline = time.monotonic() + 30
        resp = None
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                _, err = proc.communicate()
                pytest.fail(f"server exited {proc.returncode}: {err.decode()[-2000:]}")
            try:
                resp = _initialize(url)
                break
            except httpx.TransportError:
                time.sleep(0.2)
        assert resp is not None, "server never accepted a connection"
        assert resp.status_code == 200, resp.text
        payload_line = next(
            line[len("data:") :].strip()
            for line in resp.text.splitlines()
            if line.startswith("data:")
        )
        result = json.loads(payload_line)["result"]
        assert result["serverInfo"]["name"] == "l9-ops-mcp"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def test_http_bind_error_exits_nonzero_with_message():
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        port = busy.getsockname()[1]
        env = {
            **os.environ,
            "L9_MCP_TRANSPORT": "http",
            "L9_MCP_HTTP_HOST": "127.0.0.1",
            "L9_MCP_HTTP_PORT": str(port),
            "PYTHONPATH": str(REPO_ROOT / "src"),
        }
        result = subprocess.run(
            [sys.executable, "-m", "l9_ops_mcp.server"],
            env=env,
            cwd=str(REPO_ROOT),
            capture_output=True,
            timeout=60,
        )
    assert result.returncode != 0
    assert "address already in use" in result.stderr.decode().lower()
