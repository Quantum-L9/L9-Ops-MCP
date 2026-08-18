"""MCP-surface tests for ``kernel_resolve`` (execution contract §44).

These tests import the server module and drive the tool through both the
direct Python coroutine and the FastMCP registration. They do NOT require
Neo4j, Graphiti, or any external service.

MCP SDK compatibility
---------------------

The server module imports ``FastMCP`` from ``mcp.server.fastmcp``. That
import path was removed in ``mcp>=2.0`` (which replaced FastMCP with a
different server surface). ``pyproject.toml`` pins ``mcp[cli]<2.0``; the
guard below turns any accidental unpin into a clear, actionable skip with
remediation instructions rather than a cryptic ``ModuleNotFoundError``.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

def _probe_mcp_sdk() -> tuple[bool, str]:
    """Return ``(fastmcp_available, installed_version)``.

    The 1.x and 2.x wheels both expose the ``mcp`` top-level package; only
    1.x exposes ``mcp.server.fastmcp.FastMCP``. ``mcp.__version__`` is not
    reliably populated on either, so we probe the import path directly and
    read the installed distribution version via ``importlib.metadata``.
    """

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
        f"kernel_resolve MCP tests require the FastMCP surface "
        f"(mcp<2.0). Installed mcp=={_mcp_installed}. Pin mcp[cli]<2.0 "
        f"in pyproject.toml or migrate src/l9_ops_mcp/server.py to the "
        f"mcp>=2.0 server surface before removing this guard.",
        allow_module_level=True,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def _configure_repo_root():
    os.environ["L9_OPS_MCP_REPO_ROOT"] = str(REPO_ROOT)
    yield
    os.environ.pop("L9_OPS_MCP_REPO_ROOT", None)


@pytest.fixture(scope="module")
def server_module():
    from l9_ops_mcp import server as srv

    # Reset cached resolver so the module-scoped env var is picked up.
    srv._KERNEL_REGISTRY = None
    srv._KERNEL_RESOLVER = None
    return srv


def test_kernel_resolve_registered_alongside_memory_tools(server_module):
    tool_names = asyncio.run(_list_tool_names(server_module))
    # kernel_resolve added; the four memory tools remain (contract §49).
    assert "kernel_resolve" in tool_names
    for name in (
        "memory_get_budget_slice",
        "memory_ingest_episode",
        "memory_query_context",
        "memory_invalidate_fact",
    ):
        assert name in tool_names, f"memory tool missing: {name}"


async def _list_tool_names(server_module) -> list[str]:
    tools = await server_module.mcp.list_tools()
    return [t.name for t in tools]


def test_kernel_resolve_build_happy_path(server_module):
    payload = asyncio.run(server_module.kernel_resolve(
        profile="BUILD",
        consumer="Cursor-Governance/PE",
        objective="ship slice 1",
        trust_level="L3",
        max_overload_weight=6.0,
    ))
    assert payload["status"] == "ok"
    assert payload["profile"] == "BUILD"
    assert payload["resolution_digest"]
    kernels = payload["kernels"]
    assert [k["kernel_id"] for k in kernels] == [
        "l9_coding_kernel.v1",
        "l9_build_kernel.v1",
    ]
    for k in kernels:
        assert k["sha256"]
        assert k["canonical_path"].startswith("docs/kernels/")
    # Bounded Tier-1 projection.
    ctx = payload["normative_context"]
    assert set(ctx["kernels"][0]) >= {"kernel_id", "hard_bans", "purpose", "sha256"}


def test_kernel_resolve_unknown_profile_returns_stable_error(server_module):
    payload = asyncio.run(server_module.kernel_resolve(
        profile="NOT_A_PROFILE",
        consumer="PE",
        objective="x",
        trust_level="L3",
        max_overload_weight=6.0,
    ))
    assert payload["status"] == "error"
    assert payload["code"] == "KERNEL_PROFILE_UNKNOWN"


def test_kernel_resolve_insufficient_trust_returns_stable_error(server_module):
    payload = asyncio.run(server_module.kernel_resolve(
        profile="BUILD",
        consumer="PE",
        objective="x",
        trust_level="L2",
        max_overload_weight=6.0,
    ))
    assert payload["status"] == "error"
    assert payload["code"] == "KERNEL_TRUST_INSUFFICIENT"


def test_kernel_resolve_budget_exceeded_returns_stable_error(server_module):
    payload = asyncio.run(server_module.kernel_resolve(
        profile="BUILD",
        consumer="PE",
        objective="x",
        trust_level="L3",
        max_overload_weight=0.5,
    ))
    assert payload["status"] == "error"
    assert payload["code"] == "KERNEL_BUDGET_EXCEEDED"


def test_kernel_resolve_integrity_failure_cannot_return_success(
    server_module, tmp_path, monkeypatch
):
    """Simulate a corrupted retrieval index and prove the MCP tool refuses.

    Copies the real repo to tmp_path, mutates one kernel file so its actual
    SHA-256 no longer matches the index, and confirms kernel_resolve responds
    with KERNEL_DIGEST_MISMATCH rather than silently returning success.
    """
    import shutil

    # Copy just the subset needed for the resolver.
    fake_root = tmp_path / "repo"
    shutil.copytree(REPO_ROOT, fake_root, dirs_exist_ok=False, symlinks=False,
                    ignore=shutil.ignore_patterns(
                        "__pycache__", ".git", "dist", "build",
                        "*.egg-info", "node_modules"))
    # Corrupt one canonical kernel by appending a newline (changes hash).
    target = fake_root / "docs/kernels/R5/l9_build_kernel.v1.md"
    target.write_bytes(target.read_bytes() + b"\n")

    # Point the server at the corrupted tree and reset caches.
    monkeypatch.setenv("L9_OPS_MCP_REPO_ROOT", str(fake_root))
    server_module._KERNEL_REGISTRY = None
    server_module._KERNEL_RESOLVER = None

    payload = asyncio.run(server_module.kernel_resolve(
        profile="BUILD",
        consumer="PE",
        objective="x",
        trust_level="L3",
        max_overload_weight=6.0,
    ))
    assert payload["status"] == "error"
    assert payload["code"] == "KERNEL_DIGEST_MISMATCH"

    # Restore the pristine cache for later tests in this module.
    server_module._KERNEL_REGISTRY = None
    server_module._KERNEL_RESOLVER = None


def test_no_graphiti_or_neo4j_import_reachable_from_kernel_modules():
    """Contract §45: kernel modules must not import Graphiti/Neo4j/memory."""
    import ast

    forbidden = {"graphiti_core", "neo4j"}
    for name in ("kernel_models", "kernel_registry", "kernel_resolver"):
        src = (REPO_ROOT / "src/l9_ops_mcp" / f"{name}.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    root = a.name.split(".")[0]
                    assert root not in forbidden, f"{name}.py imports {a.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root = node.module.split(".")[0]
                    assert root not in forbidden, f"{name}.py imports {node.module}"
