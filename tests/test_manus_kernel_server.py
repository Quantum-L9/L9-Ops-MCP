# >>> l9:meta >>>
# id: L9-Ops-MCP.test.tests_test_manus_kernel_server__py
# title: test manus kernel server
# artifact_type: test
# mcp_primitive: none
# callable: false
# retrievable: false
# injectable: false
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: tests/test_manus_kernel_server.py
# content_hash: d3586bc7f6b49d37e8e3d38d7db38f7b8489802f48ec4b4becbaa92425df4086
# token_cost_estimate: 879
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
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


def test_manus_facade_forces_strict_integrity(monkeypatch):
    """Every connector resolution enables per-call canonical digest verification."""

    from l9_ops_mcp import manus_kernel_server

    monkeypatch.delenv("L9_KERNEL_STRICT_INTEGRITY", raising=False)
    payload = asyncio.run(
        manus_kernel_server.kernel_resolve(
            profile="BUILD",
            consumer="Manus connector test",
            objective="resolve bounded authority",
            trust_level="L3",
            max_overload_weight=6.0,
        )
    )

    assert os.environ["L9_KERNEL_STRICT_INTEGRITY"] == "1"
    assert payload["status"] == "ok"
    assert payload["profile"] == "BUILD"
    assert payload["resolution_digest"]


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
