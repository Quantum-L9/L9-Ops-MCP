"""RG-06: memory_invalidate_fact targets the fact edge and reports the real outcome;
invalidated facts are not served afterwards. In-process fake graph; no Neo4j.

U-03 (graphiti-core 0.31.2): Graphiti search does NOT exclude edges whose
invalid_at is set unless SearchFilters.invalid_at is supplied
(search_filters.edge_search_filter_query_constructor only emits an invalid_at
clause when filters.invalid_at is not None), so the read side filters explicitly.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any

import pytest
from graphiti_core.edges import EntityEdge
from graphiti_core.search.search_config import SearchResults
from graphiti_core.search.search_filters import ComparisonOperator

import l9_ops_mcp.graphiti_client as graphiti_client
import l9_ops_mcp.hydrator as hydrator
import l9_ops_mcp.server as server

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
_EDGE_MATCH = re.compile(
    r"MATCH\s*\(\w*(:\w+)?\)\s*-\s*\[\s*e\s*:\s*RELATES_TO\s*\{\s*uuid:\s*\$uuid\s*\}\s*\]\s*->"
)


def _edge(uuid: str, fact: str) -> EntityEdge:
    return EntityEdge(
        uuid=uuid,
        group_id="global__conventions",
        source_node_uuid="s",
        target_node_uuid="t",
        created_at=NOW,
        name="RELATES_TO",
        fact=fact,
    )


class _FakeDriver:
    """Neo4j semantics for the two query shapes: node match vs RELATES_TO match."""

    def __init__(self, edges: dict[str, EntityEdge], fail: bool = False) -> None:
        self.edges = edges
        self.fail = fail
        self.queries: list[str] = []

    async def execute_query(
        self, query: str, **kwargs: Any
    ) -> tuple[list[dict[str, Any]], Any, list[str]]:
        self.queries.append(query)
        if self.fail:
            raise RuntimeError("neo4j unavailable")
        uuid = kwargs["uuid"]
        if _EDGE_MATCH.search(query) and uuid in self.edges:
            edge = self.edges[uuid]
            edge.invalid_at = kwargs["ts"]
            edge.expired_at = edge.expired_at or kwargs["ts"]
            edge.attributes = {**edge.attributes, "invalid_reason": kwargs["reason"]}
            return [{"uuid": uuid}], None, ["uuid"]
        # MATCH (n {uuid: $uuid}) matches nodes only: facts are relationships.
        return [], None, []


class _FakeGraph:
    def __init__(self, edges: list[EntityEdge], fail: bool = False) -> None:
        self.by_uuid = {e.uuid: e for e in edges}
        self.driver = _FakeDriver(self.by_uuid, fail=fail)
        self.search_filters: list[Any] = []

    async def search_(self, **kwargs: Any) -> SearchResults:
        # Mirrors graphiti-core: no invalid_at clause unless the filter asks for it.
        self.search_filters.append(kwargs.get("search_filter"))
        edges = list(self.by_uuid.values())
        return SearchResults(edges=edges, edge_reranker_scores=[1.0] * len(edges))


@pytest.fixture
def graph(monkeypatch: pytest.MonkeyPatch) -> _FakeGraph:
    g = _FakeGraph([_edge("e-1", "stale fact"), _edge("e-2", "current fact")])

    async def _get() -> _FakeGraph:
        return g

    monkeypatch.setattr(graphiti_client, "get_graphiti", _get)
    monkeypatch.setattr(hydrator, "get_graphiti", _get)
    return g


def test_invalidates_the_fact_edge(graph: _FakeGraph) -> None:
    result = asyncio.run(server.memory_invalidate_fact("e-1", "superseded"))
    assert graph.by_uuid["e-1"].invalid_at is not None
    assert graph.by_uuid["e-2"].invalid_at is None
    assert result["invalidated"] == "e-1"
    assert result["reason"] == "superseded"
    assert "ts" in result


def test_unknown_uuid_is_not_found(graph: _FakeGraph) -> None:
    result = asyncio.run(server.memory_invalidate_fact("missing", "x"))
    assert result.get("status") == "not_found"
    assert result.get("invalidated") is None
    assert all(e.invalid_at is None for e in graph.by_uuid.values())


def test_driver_error_is_a_tool_error_not_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from mcp.server.fastmcp.exceptions import ToolError

    g = _FakeGraph([_edge("e-1", "fact")], fail=True)

    async def _get() -> _FakeGraph:
        return g

    monkeypatch.setattr(graphiti_client, "get_graphiti", _get)
    with pytest.raises(ToolError):
        asyncio.run(
            server.mcp.call_tool("memory_invalidate_fact", {"entity_uuid": "e-1", "reason": "r"})
        )


def test_invalidated_fact_is_not_served_by_hydrate(graph: _FakeGraph) -> None:
    asyncio.run(server.memory_invalidate_fact("e-1", "superseded"))
    p = asyncio.run(hydrator.hydrate("q", "a", 4000, "L5", "s"))
    served = [
        f.uuid
        for f in p.context_slice.tier1_load_bearing
        + p.context_slice.tier2_examples
        + p.context_slice.tier3_stakes
    ]
    assert "e-1" not in served
    assert "e-2" in served
    # and the search itself asked graphiti to exclude invalidated edges
    flt = graph.search_filters[-1]
    assert flt is not None and flt.invalid_at is not None
    assert flt.invalid_at[0][0].comparison_operator == ComparisonOperator.is_null
