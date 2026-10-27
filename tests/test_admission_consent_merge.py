"""RG-05 (D-03 A): the admission gate evaluates all five kernel criteria in order
(relevance, trust, consent, deduplication, provenance) and a duplicate is merged
(no new episode + provenance appended to the existing fact), never silently
dropped. In-process fakes; no Neo4j."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from graphiti_core.edges import EntityEdge
from graphiti_core.search.search_config import SearchResults

import l9_ops_mcp.admission as adm
import l9_ops_mcp.memory_ops as memory_ops
import l9_ops_mcp.server as server
from l9_ops_mcp.admission import evaluate
from l9_ops_mcp.models import MemoryCandidate

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    log = tmp_path / "log.jsonl"
    q = tmp_path / "q"
    monkeypatch.setattr(adm, "LOG", log)
    monkeypatch.setattr(adm, "QUARANTINE", q)
    return log, q


def _lines(log: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in log.read_text().splitlines()]


async def _no_dup(_body: str) -> bool:
    return False


def _candidate(**kw: Any) -> MemoryCandidate:
    base: dict[str, Any] = {
        "body": "an architectural decision",
        "source_agent_id": "a",
        "session_id": "s",
        "semantic_score": 0.9,
        "trust_level": "L2",
    }
    base.update(kw)
    return MemoryCandidate(**base)


# --- consent -------------------------------------------------------------


def test_consent_defaults_to_deny_for_external_sharing() -> None:
    c = _candidate()
    assert c.external_sharing is False
    assert c.consent == "deny"


def test_external_sharing_without_consent_is_blocked_and_logged(paths) -> None:
    log, _ = paths
    ok, disp = asyncio.run(evaluate(_candidate(external_sharing=True), _no_dup))
    assert (ok, disp) == (False, "block:consent")
    last = _lines(log)[-1]
    assert last["criterion"] == "consent"
    assert last["disposition"] == "block"


def test_external_sharing_with_explicit_consent_is_admitted(paths) -> None:
    ok, disp = asyncio.run(evaluate(_candidate(external_sharing=True, consent="granted"), _no_dup))
    assert (ok, disp) == (True, "admit")


def test_internal_write_needs_no_consent(paths) -> None:
    ok, disp = asyncio.run(evaluate(_candidate(), _no_dup))
    assert (ok, disp) == (True, "admit")


def test_criteria_order_trust_before_consent_before_dedup(paths) -> None:
    calls: list[str] = []

    async def dup(_body: str) -> bool:
        calls.append("dedup")
        return True

    low_trust = _candidate(trust_level="L1", external_sharing=True)
    assert asyncio.run(evaluate(low_trust, dup)) == (False, "block:trust")
    no_consent = _candidate(external_sharing=True)
    assert asyncio.run(evaluate(no_consent, dup)) == (False, "block:consent")
    assert calls == []  # consent is decided before the deduplication graph check


# --- merge ---------------------------------------------------------------


class _FakeDriver:
    def __init__(self, known: set[str]) -> None:
        self.known = known
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def execute_query(self, query: str, **kwargs: Any):
        self.calls.append((query, kwargs))
        if "RELATES_TO" in query and kwargs.get("uuid") in self.known:
            return [{"uuid": kwargs["uuid"]}], None, ["uuid"]
        return [], None, []


class _FakeGraph:
    def __init__(self, fact: str, known: set[str] | None = None) -> None:
        self.edge = EntityEdge(
            uuid="edge-1",
            group_id="session__current",
            source_node_uuid="s",
            target_node_uuid="t",
            created_at=NOW,
            name="RELATES_TO",
            fact=fact,
        )
        self.driver = _FakeDriver({"edge-1"} if known is None else known)
        self.episodes: list[dict[str, Any]] = []

    async def search_(self, **kwargs: Any) -> SearchResults:
        return SearchResults(edges=[self.edge], edge_reranker_scores=[1.0])

    async def add_episode(self, **kwargs: Any) -> None:
        self.episodes.append(kwargs)


def _patch(monkeypatch: pytest.MonkeyPatch, g: _FakeGraph) -> None:
    async def _get() -> _FakeGraph:
        return g

    monkeypatch.setattr(memory_ops, "get_graphiti", _get)


def test_duplicate_is_merged_with_provenance_append(paths, monkeypatch) -> None:
    log, _ = paths
    g = _FakeGraph("an architectural decision")
    _patch(monkeypatch, g)
    c = _candidate(session_id="s-2", source_agent_id="agent-b")
    result = asyncio.run(memory_ops.ingest_episode(c))

    assert g.episodes == []  # no new episode
    assert result["disposition"] == "merge:dedup"
    assert result["merged_into"] == "edge-1"
    query, params = g.driver.calls[-1]
    assert "RELATES_TO" in query and "l9_provenance" in query
    assert params["uuid"] == "edge-1"
    prov = json.loads(params["provenance"])
    assert prov == {"agent": "agent-b", "session": "s-2", "ts": c.origin_timestamp.isoformat()}
    dispositions = [(line["criterion"], line["disposition"]) for line in _lines(log)]
    assert ("deduplication", "merge") in dispositions
    assert ("deduplication", "merged") in dispositions


def test_merge_failure_quarantines_the_candidate(paths, monkeypatch) -> None:
    log, q = paths
    g = _FakeGraph("an architectural decision", known=set())  # edge vanished
    _patch(monkeypatch, g)
    result = asyncio.run(memory_ops.ingest_episode(_candidate()))
    assert result["admitted"] is False
    assert result["disposition"] == "quarantine:merge"
    files = list(q.glob("*.json"))
    assert len(files) == 1
    assert json.loads(files[0].read_text())["body"] == "an architectural decision"
    last = _lines(log)[-1]
    assert last["criterion"] == "deduplication"
    assert last["disposition"] == "quarantine"
    assert last["reason"]


def test_duplicate_without_provenance_is_blocked_not_merged(paths, monkeypatch) -> None:
    g = _FakeGraph("an architectural decision")
    _patch(monkeypatch, g)
    result = asyncio.run(memory_ops.ingest_episode(_candidate(session_id="")))
    assert result["disposition"] == "block:provenance"
    assert g.driver.calls == []


def test_mcp_ingest_carries_consent(paths, monkeypatch) -> None:
    g = _FakeGraph("something else entirely")
    _patch(monkeypatch, g)
    blocked = asyncio.run(
        server.memory_ingest_episode(
            body="share me", source_agent_id="a", session_id="s", external_sharing=True
        )
    )
    assert blocked == {"admitted": False, "disposition": "block:consent"}
    admitted = asyncio.run(
        server.memory_ingest_episode(
            body="share me",
            source_agent_id="a",
            session_id="s",
            external_sharing=True,
            consent="granted",
        )
    )
    assert admitted["admitted"] is True
    assert len(g.episodes) == 1
