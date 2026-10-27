"""RG-03 (D-02 A): memory_query_context and `cli query` are trust-scoped exactly
like hydrate. In-process fake graph; no Neo4j."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from typing import Any

import pytest
from graphiti_core.edges import EntityEdge
from graphiti_core.search.search_config import SearchResults
from mcp.server.fastmcp.exceptions import ToolError

import l9_ops_mcp.cli as cli
import l9_ops_mcp.graphiti_client as graphiti_client
import l9_ops_mcp.hydrator as hydrator
import l9_ops_mcp.server as server

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class _FakeGraph:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.edges = [
            EntityEdge(
                uuid="u1",
                group_id="global__decisions",
                source_node_uuid="s",
                target_node_uuid="t",
                created_at=NOW,
                valid_at=NOW,
                name="RELATES_TO",
                fact="a global decision",
            )
        ]

    async def search(self, **kwargs: Any) -> list[EntityEdge]:  # legacy unscoped surface
        self.calls.append(kwargs)
        return list(self.edges)

    async def search_(self, **kwargs: Any) -> SearchResults:
        self.calls.append(kwargs)
        return SearchResults(edges=list(self.edges), edge_reranker_scores=[1.0])


@pytest.fixture
def graph(monkeypatch: pytest.MonkeyPatch) -> _FakeGraph:
    g = _FakeGraph()

    async def _get() -> _FakeGraph:
        return g

    monkeypatch.setattr(graphiti_client, "get_graphiti", _get)
    monkeypatch.setattr(hydrator, "get_graphiti", _get)
    return g


def _call(args: dict[str, Any]) -> Any:
    return asyncio.run(server.mcp.call_tool("memory_query_context", args))


def _structured(result: Any) -> dict[str, Any]:
    # FastMCP.call_tool(convert_result=True) returns (content, structured) for dict tools
    if isinstance(result, tuple):
        return result[1]["result"] if "result" in result[1] else result[1]
    return result


def test_call_without_trust_input_is_rejected(graph: _FakeGraph) -> None:
    with pytest.raises(ToolError):
        _call({"query": "decision"})
    assert graph.calls == []


def test_l0_returns_no_facts_and_never_searches(graph: _FakeGraph) -> None:
    out = _structured(_call({"query": "decision", "agent_id": "a", "trust_level": "L0"}))
    assert out["facts"] == []
    assert graph.calls == []


def test_bogus_trust_is_a_tool_error(graph: _FakeGraph) -> None:
    with pytest.raises(ToolError, match="trust_level"):
        _call({"query": "decision", "agent_id": "a", "trust_level": "bogus"})
    assert graph.calls == []


def test_l2_search_is_scoped_to_allowed_scopes(graph: _FakeGraph) -> None:
    out = _structured(_call({"query": "decision", "agent_id": "a", "trust_level": "L2"}))
    assert graph.calls[-1]["group_ids"] == [
        "global__conventions",
        "agent__a",
        "session__current",
    ]
    assert set(out["facts"][0]) == {"fact", "uuid", "valid_at"}


def test_requested_group_outside_allowed_scopes_is_rejected(graph: _FakeGraph) -> None:
    with pytest.raises(ToolError, match="not permitted"):
        _call(
            {
                "query": "decision",
                "agent_id": "a",
                "trust_level": "L2",
                "group_ids": ["global:decisions"],
            }
        )
    assert graph.calls == []


def test_requested_subset_narrows_search(graph: _FakeGraph) -> None:
    _call(
        {
            "query": "decision",
            "agent_id": "a",
            "trust_level": "L4",
            "group_ids": ["global:decisions"],
        }
    )
    assert graph.calls[-1]["group_ids"] == ["global__decisions"]


def test_cli_query_obeys_the_same_rule(graph: _FakeGraph, monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["cli", "query", json.dumps({"query": "decision"})])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code not in (0, None)
    assert graph.calls == []

    monkeypatch.setattr(
        sys,
        "argv",
        ["cli", "query", json.dumps({"query": "d", "agent_id": "a", "trust_level": "L0"})],
    )
    cli.main()
    assert json.loads(capsys.readouterr().out)["facts"] == []
    assert graph.calls == []
