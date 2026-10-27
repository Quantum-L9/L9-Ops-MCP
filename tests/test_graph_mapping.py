"""RG-04: Graphiti results are consumed through fields and APIs that exist.

Uses real graphiti_core EntityEdge / SearchResults objects behind an
in-process fake graph; no Neo4j.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import pytest
from graphiti_core.edges import EntityEdge
from graphiti_core.search.search_config import SearchResults

import l9_ops_mcp.admission as adm
import l9_ops_mcp.hydrator as hydrator
import l9_ops_mcp.memory_ops as memory_ops
from l9_ops_mcp.models import MemoryCandidate

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _edge(fact: str, group_id: str = "g", uuid: str | None = None) -> EntityEdge:
    kwargs: dict[str, Any] = {
        "group_id": group_id,
        "source_node_uuid": "s",
        "target_node_uuid": "t",
        "created_at": NOW,
        "name": "RELATES_TO",
        "fact": fact,
    }
    if uuid is not None:
        kwargs["uuid"] = uuid
    return EntityEdge(**kwargs)


class _FakeGraph:
    """Implements the graphiti-core 0.31 surface the service uses."""

    def __init__(self, edges: list[EntityEdge], scores: list[float] | None = None) -> None:
        self.edges = edges
        self.scores = scores if scores is not None else []
        self.calls: list[dict[str, Any]] = []
        self.episodes: list[dict[str, Any]] = []

    async def search_(self, **kwargs: Any) -> SearchResults:
        self.calls.append(kwargs)
        limit = kwargs["config"].limit
        return SearchResults(edges=self.edges[:limit], edge_reranker_scores=self.scores[:limit])

    async def search(self, **kwargs: Any) -> list[EntityEdge]:  # legacy surface
        self.calls.append(kwargs)
        return list(self.edges)

    async def add_episode(self, **kwargs: Any) -> None:
        self.episodes.append(kwargs)


def _patch(monkeypatch: pytest.MonkeyPatch, module: Any, g: _FakeGraph) -> None:
    async def _get() -> _FakeGraph:
        return g

    monkeypatch.setattr(module, "get_graphiti", _get)


def test_context_fact_carries_edge_group_id_and_reranker_score(monkeypatch) -> None:
    g = _FakeGraph(
        [_edge("alpha fact", "global__conventions"), _edge("beta fact", "agent__a")],
        scores=[0.9, 0.4],
    )
    _patch(monkeypatch, hydrator, g)
    p = asyncio.run(hydrator.hydrate("q", "a", 4000, "L2", "s"))
    facts = p.context_slice.tier1_load_bearing + p.context_slice.tier2_examples
    by_fact = {f.fact: f for f in facts}
    assert by_fact["alpha fact"].group_id == "global__conventions"
    assert by_fact["beta fact"].group_id == "agent__a"
    assert by_fact["alpha fact"].score == pytest.approx(0.9)
    assert by_fact["beta fact"].score == pytest.approx(0.4)
    assert p.relevance_signal == "rrf"


def test_ordinal_fallback_is_explicit_when_scores_unavailable(monkeypatch) -> None:
    g = _FakeGraph([_edge("first"), _edge("second"), _edge("third")], scores=[])
    _patch(monkeypatch, hydrator, g)
    p = asyncio.run(hydrator.hydrate("q", "a", 4000, "L5", "s"))
    facts = p.context_slice.tier1_load_bearing + p.context_slice.tier2_examples
    scores = {f.fact: f.score for f in facts}
    assert scores["first"] > scores["second"] > scores["third"] > 0.0
    assert p.relevance_signal == "ordinal"


def test_budget_ordering_follows_relevance(monkeypatch) -> None:
    # Search order differs from score order; tier 1 (load-bearing) must hold the
    # most relevant facts, not the first ones returned.
    g = _FakeGraph(
        [_edge("low relevance", uuid="low"), _edge("high relevance", uuid="high")],
        scores=[0.1, 0.8],
    )
    _patch(monkeypatch, hydrator, g)
    p = asyncio.run(hydrator.hydrate("q", "a", 4000, "L5", "s"))
    assert [f.uuid for f in p.context_slice.tier1_load_bearing] == ["high"]
    assert [f.uuid for f in p.context_slice.tier2_examples] == ["low"]


def test_exact_duplicate_body_is_detected(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(adm, "LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(adm, "QUARANTINE", tmp_path / "q")
    body = "Graphiti is the L9 graph backend."
    g = _FakeGraph([_edge("  graphiti is the L9 graph   backend ", "session__current")])
    _patch(monkeypatch, memory_ops, g)
    c = MemoryCandidate(body=body, source_agent_id="a", session_id="s", semantic_score=0.9)
    result = asyncio.run(memory_ops.ingest_episode(c))
    assert result["admitted"] is False
    assert "dedup" in str(result["disposition"])
    assert g.episodes == []
    # the duplicate search is scoped to the target group
    assert g.calls[-1]["group_ids"] == ["session__current"]


def test_non_duplicate_is_admitted(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(adm, "LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(adm, "QUARANTINE", tmp_path / "q")
    g = _FakeGraph([_edge("an unrelated fact", "session__current")])
    _patch(monkeypatch, memory_ops, g)
    c = MemoryCandidate(body="a new fact", source_agent_id="a", session_id="s", semantic_score=0.9)
    result = asyncio.run(memory_ops.ingest_episode(c))
    assert result["admitted"] is True
    assert len(g.episodes) == 1
