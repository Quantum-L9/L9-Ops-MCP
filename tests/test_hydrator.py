"""Hydrator regression tests (RG-02). In-process fake graph; no Neo4j."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

import l9_ops_mcp.hydrator as hydrator
import l9_ops_mcp.server as server_module


class _FakeGraph:
    def __init__(self, results: list[Any] | None = None) -> None:
        self.search_calls: list[dict[str, Any]] = []
        self._results = results or []

    async def search(self, **kwargs: Any) -> list[Any]:
        self.search_calls.append(kwargs)
        return list(self._results)


class _Edge:
    def __init__(self, fact: str, group_id: str = "g") -> None:
        self.uuid = f"u-{fact}"
        self.fact = fact
        self.group_id = group_id
        self.valid_at = None
        self.invalid_at = None


@pytest.fixture
def fake_graph(monkeypatch: pytest.MonkeyPatch) -> _FakeGraph:
    g = _FakeGraph([_Edge("leaked global decision", "global__decisions")])

    async def _get() -> _FakeGraph:
        return g

    monkeypatch.setattr(hydrator, "get_graphiti", _get)
    return g


def test_l0_never_searches_and_returns_empty_context(fake_graph: _FakeGraph) -> None:
    payload = asyncio.run(hydrator.hydrate("task", "agent", 4000, "L0", "s1"))
    assert fake_graph.search_calls == []
    assert payload.allowed_scopes == []
    sl = payload.context_slice
    assert sl.tier1_load_bearing == [] and sl.tier2_examples == [] and sl.tier3_stakes == []
    assert sl.token_count == 0
    assert payload.budget_remaining_tokens == 4000
    assert payload.readonly is True


def test_unknown_trust_level_rejected_before_graph_access(fake_graph: _FakeGraph) -> None:
    with pytest.raises(ValueError, match="trust_level"):
        asyncio.run(hydrator.hydrate("task", "agent", 4000, "bogus", "s1"))  # type: ignore[arg-type]
    assert fake_graph.search_calls == []


def test_l5_remains_unrestricted(fake_graph: _FakeGraph) -> None:
    asyncio.run(hydrator.hydrate("task", "agent", 4000, "L5", "s1"))
    assert len(fake_graph.search_calls) == 1
    assert fake_graph.search_calls[0]["group_ids"] is None


def test_mcp_tool_l0_returns_empty_context(fake_graph: _FakeGraph) -> None:
    result = asyncio.run(
        server_module.memory_get_budget_slice(
            task_type="task", agent_id="agent", token_budget=1000, trust_level="L0", session_id="s"
        )
    )
    assert fake_graph.search_calls == []
    assert result["allowed_scopes"] == []
    assert result["context_slice"]["token_count"] == 0  # type: ignore[index]


def test_mcp_tool_bogus_trust_is_a_tool_error(fake_graph: _FakeGraph) -> None:
    from mcp.server.fastmcp.exceptions import ToolError

    with pytest.raises(ToolError, match="trust_level"):
        asyncio.run(
            server_module.mcp.call_tool(
                "memory_get_budget_slice",
                {
                    "task_type": "task",
                    "agent_id": "agent",
                    "token_budget": 1000,
                    "trust_level": "bogus",
                    "session_id": "s",
                },
            )
        )
    assert fake_graph.search_calls == []
