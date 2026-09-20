"""Safety tests for the restricted Manus kernel-authority MCP facade."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def configure_repository_root():
    """Point the native resolver to this immutable test checkout."""

    prior = os.environ.get("L9_OPS_MCP_REPO_ROOT")
    os.environ["L9_OPS_MCP_REPO_ROOT"] = str(REPO_ROOT)
    yield
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
