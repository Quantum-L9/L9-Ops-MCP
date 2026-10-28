# --- L9_META ---
# l9_schema: 1
# origin: l9-ops-mcp
# layer: test
# artifact_type: test_module
# component: manus_kernel_server_tests
# tags: [manus, mcp, kernel-authority, tests]
# owner: Quantum-L9
# retrieval: on_demand
# status: active
# --- /L9_META ---
"""Safety tests for the restricted Manus kernel-authority MCP facade."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest


def _probe_mcp_sdk() -> tuple[bool, str]:
    """Return whether the pinned FastMCP surface is importable and its version."""

    from importlib.metadata import PackageNotFoundError, version

    try:
        installed = version("mcp")
    except PackageNotFoundError:
        installed = "not-installed"
    try:
        from mcp.server.fastmcp import FastMCP  # noqa: F401
    except ImportError:
        return False, installed
    return True, installed


_fastmcp_ok, _mcp_installed = _probe_mcp_sdk()
if not _fastmcp_ok:
    pytest.skip(
        f"Manus kernel facade tests require FastMCP (mcp<2.0). Installed "
        f"mcp=={_mcp_installed}. Pin mcp[cli]<2.0 or migrate the facade before "
        "removing this guard.",
        allow_module_level=True,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def configure_repository_root():
    """Isolate native resolver state from other MCP test modules."""

    from l9_ops_mcp import server as native_server

    prior = os.environ.get("L9_OPS_MCP_REPO_ROOT")
    os.environ["L9_OPS_MCP_REPO_ROOT"] = str(REPO_ROOT)
    native_server._KERNEL_REGISTRY = None
    native_server._KERNEL_RESOLVER = None
    yield
    native_server._KERNEL_REGISTRY = None
    native_server._KERNEL_RESOLVER = None
    if prior is None:
        os.environ.pop("L9_OPS_MCP_REPO_ROOT", None)
    else:
        os.environ["L9_OPS_MCP_REPO_ROOT"] = prior


async def _tool_names() -> list[str]:
    from l9_ops_mcp.manus_kernel_server import mcp

    return [tool.name for tool in await mcp.list_tools()]


def test_manus_facade_exposes_only_kernel_resolve():
    """The connector must not inherit native memory-plane tool registration."""

    assert asyncio.run(_tool_names()) == ["kernel_resolve"]


def _count_integrity_checks(monkeypatch) -> list[int]:
    """Load the native registry and count its per-call integrity verifications."""

    from l9_ops_mcp import server as native_server

    native_server._get_resolver(strict_integrity=False)
    registry = native_server._KERNEL_REGISTRY
    assert registry is not None
    calls: list[int] = []
    original = registry.verify_integrity

    def counting_verify() -> None:
        calls.append(1)
        original()

    monkeypatch.setattr(registry, "verify_integrity", counting_verify)
    return calls


def _resolve(module) -> dict[str, object]:
    return asyncio.run(
        module.kernel_resolve(
            profile="BUILD",
            consumer="Manus connector test",
            objective="resolve bounded authority",
            trust_level="L3",
            max_overload_weight=6.0,
        )
    )


def test_manus_facade_forces_strict_integrity(monkeypatch):
    """Every connector resolution enables per-call canonical digest verification."""

    from l9_ops_mcp import manus_kernel_server

    monkeypatch.delenv("L9_KERNEL_STRICT_INTEGRITY", raising=False)
    calls = _count_integrity_checks(monkeypatch)
    payload = _resolve(manus_kernel_server)

    assert calls == [1]
    assert payload["status"] == "ok"
    assert payload["profile"] == "BUILD"
    assert payload["resolution_digest"]


def test_manus_facade_leaves_process_environment_unchanged(monkeypatch):
    """OBS-14: strictness is per call, never switched on process-wide."""

    from l9_ops_mcp import manus_kernel_server

    monkeypatch.delenv("L9_KERNEL_STRICT_INTEGRITY", raising=False)
    before = dict(os.environ)
    _resolve(manus_kernel_server)

    assert dict(os.environ) == before
    assert "L9_KERNEL_STRICT_INTEGRITY" not in os.environ


def test_native_call_after_manus_call_stays_non_strict(monkeypatch):
    """OBS-14: a Manus call must not turn strict integrity on for the main server."""

    from l9_ops_mcp import manus_kernel_server
    from l9_ops_mcp import server as native_server

    monkeypatch.delenv("L9_KERNEL_STRICT_INTEGRITY", raising=False)
    calls = _count_integrity_checks(monkeypatch)
    manus_payload = _resolve(manus_kernel_server)
    native_payload = _resolve(native_server)

    assert calls == [1]
    assert native_payload == manus_payload


def test_native_env_strictness_still_honoured(monkeypatch):
    """The documented env switch keeps working for the main server."""

    from l9_ops_mcp import server as native_server

    monkeypatch.setenv("L9_KERNEL_STRICT_INTEGRITY", "1")
    calls = _count_integrity_checks(monkeypatch)
    payload = _resolve(native_server)

    assert calls == [1]
    assert payload["status"] == "ok"


def test_manus_facade_preserves_native_error_envelope():
    """Invalid requests remain stable domain errors rather than tracebacks."""

    from l9_ops_mcp import manus_kernel_server

    payload = asyncio.run(
        manus_kernel_server.kernel_resolve(
            profile="UNKNOWN",
            consumer="Manus connector test",
            objective="reject unsupported profile",
            trust_level="L3",
            max_overload_weight=6.0,
        )
    )

    assert payload["status"] == "error"
    assert payload["code"] == "KERNEL_PROFILE_UNKNOWN"
