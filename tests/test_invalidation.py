"""RG-06: memory_invalidate_fact targets the fact edge and reports the real outcome;
invalidated facts are not served afterwards. In-process fake graph; no Neo4j.

F-pr38-01: invalidation is a memory write, so it is gated by the trust ladder
(L3+, trust_ladder_kernel memory_write_via_admission_gate) and scoped to
allowed_scopes(agent_id, trust_level) inside the Cypher itself.

U-03 (graphiti-core 0.31.2): Graphiti search does NOT exclude edges whose
invalid_at is set unless SearchFilters.invalid_at is supplied
(search_filters.edge_search_filter_query_constructor only emits an invalid_at
clause when filters.invalid_at is not None), so the read side filters explicitly.
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from graphiti_core.edges import EntityEdge
from graphiti_core.search.search_config import SearchResults
from graphiti_core.search.search_filters import ComparisonOperator

import l9_ops_mcp.admission as adm
import l9_ops_mcp.graphiti_client as graphiti_client
import l9_ops_mcp.hydrator as hydrator
import l9_ops_mcp.server as server

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
_EDGE_MATCH = re.compile(
    r"MATCH\s*\(\w*(:\w+)?\)\s*-\s*\[\s*e\s*:\s*RELATES_TO\s*\{\s*uuid:\s*\$uuid\s*\}\s*\]\s*->"
)
_SCOPE_PREDICATE = re.compile(r"WHERE\s+\$all_scopes\s+OR\s+e\.group_id\s+IN\s+\$scopes")


def _edge(uuid: str, fact: str, group_id: str = "global__conventions") -> EntityEdge:
    return EntityEdge(
        uuid=uuid,
        group_id=group_id,
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
            # Neo4j applies the WHERE clause; without one every edge matches.
            if _SCOPE_PREDICATE.search(query) and not (
                kwargs["all_scopes"] or edge.group_id in kwargs["scopes"]
            ):
                return [], None, []
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


@pytest.fixture(autouse=True)
def admission_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    log = tmp_path / "admission.jsonl"
    monkeypatch.setattr(adm, "LOG", log)
    return log


def _log_lines(log: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in log.read_text().splitlines()]


@pytest.fixture
def graph(monkeypatch: pytest.MonkeyPatch) -> _FakeGraph:
    g = _FakeGraph(
        [
            _edge("e-1", "stale fact"),
            _edge("e-2", "current fact"),
            _edge("d-1", "a decision", group_id="global__decisions"),
        ]
    )

    async def _get() -> _FakeGraph:
        return g

    monkeypatch.setattr(graphiti_client, "get_graphiti", _get)
    monkeypatch.setattr(hydrator, "get_graphiti", _get)
    return g


def test_invalidates_the_fact_edge(graph: _FakeGraph) -> None:
    result = asyncio.run(server.memory_invalidate_fact("e-1", "superseded", "planner", "L3"))
    assert graph.by_uuid["e-1"].invalid_at is not None
    assert graph.by_uuid["e-2"].invalid_at is None
    assert result["invalidated"] == "e-1"
    assert result["reason"] == "superseded"
    assert "ts" in result


def test_unknown_uuid_is_not_found(graph: _FakeGraph) -> None:
    result = asyncio.run(server.memory_invalidate_fact("missing", "x", "planner", "L3"))
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
            server.mcp.call_tool(
                "memory_invalidate_fact",
                {"entity_uuid": "e-1", "reason": "r", "agent_id": "a", "trust_level": "L3"},
            )
        )


def test_invalidated_fact_is_not_served_by_hydrate(graph: _FakeGraph) -> None:
    asyncio.run(server.memory_invalidate_fact("e-1", "superseded", "planner", "L3"))
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


# --- trust ladder (F-pr38-01) ---------------------------------------------


@pytest.mark.parametrize("level", ["L0", "L1", "L2"])
def test_below_l3_is_denied_without_graph_access(
    graph: _FakeGraph, admission_log: Path, level: str
) -> None:
    result = asyncio.run(server.memory_invalidate_fact("d-1", "hide it", "mallory", level))
    assert result["status"] == "denied"
    assert result["invalidated"] is None
    assert graph.driver.queries == []
    assert all(e.invalid_at is None for e in graph.by_uuid.values())
    last = _log_lines(admission_log)[-1]
    assert (last["criterion"], last["disposition"]) == ("invalidate", "denied")
    assert (last["agent"], last["trust_level"], last["uuid"]) == ("mallory", level, "d-1")


def test_out_of_scope_edge_is_not_found_and_unchanged(
    graph: _FakeGraph, admission_log: Path
) -> None:
    # L3 scopes exclude global__decisions (L4+): same answer as a missing uuid.
    result = asyncio.run(server.memory_invalidate_fact("d-1", "hide it", "mallory", "L3"))
    assert result == {"status": "not_found", "invalidated": None, "uuid": "d-1"}
    assert graph.by_uuid["d-1"].invalid_at is None
    assert _log_lines(admission_log)[-1]["disposition"] == "not_found"


def test_in_scope_edge_is_invalidated_at_l4(graph: _FakeGraph, admission_log: Path) -> None:
    result = asyncio.run(server.memory_invalidate_fact("d-1", "superseded", "planner", "L4"))
    assert result["invalidated"] == "d-1"
    assert graph.by_uuid["d-1"].invalid_at is not None
    assert _log_lines(admission_log)[-1]["disposition"] == "invalidated"


def test_l5_reaches_every_group(graph: _FakeGraph) -> None:
    result = asyncio.run(server.memory_invalidate_fact("d-1", "superseded", "root", "L5"))
    assert result["invalidated"] == "d-1"


def test_scope_is_enforced_in_the_cypher(graph: _FakeGraph) -> None:
    asyncio.run(server.memory_invalidate_fact("e-1", "superseded", "planner", "L3"))
    assert _SCOPE_PREDICATE.search(graph.driver.queries[-1])


def test_unknown_trust_level_is_rejected_before_graph_access(graph: _FakeGraph) -> None:
    from l9_ops_mcp.trust_ladder import UnknownTrustLevelError

    with pytest.raises(UnknownTrustLevelError):
        asyncio.run(server.memory_invalidate_fact("d-1", "x", "a", "L9"))
    assert graph.driver.queries == []


def test_mcp_call_without_trust_arguments_is_rejected(graph: _FakeGraph) -> None:
    from mcp.server.fastmcp.exceptions import ToolError

    with pytest.raises(ToolError):
        asyncio.run(
            server.mcp.call_tool("memory_invalidate_fact", {"entity_uuid": "d-1", "reason": "r"})
        )
    assert graph.by_uuid["d-1"].invalid_at is None
