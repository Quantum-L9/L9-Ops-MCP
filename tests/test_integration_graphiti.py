"""Integration tests — Neo4j required.
Skipped automatically if L9_NEO4J_URI is not set.
Run: L9_NEO4J_URI=bolt://localhost:7687 pytest tests/test_integration_graphiti.py -v
"""

from __future__ import annotations

import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("L9_NEO4J_URI"),
    reason="L9_NEO4J_URI not set — integration tests require a live Neo4j instance",
)


@pytest.mark.asyncio
async def test_graphiti_indices_build():
    from l9_ops_mcp.graphiti_client import get_graphiti

    g = await get_graphiti()
    assert g is not None


@pytest.mark.asyncio
async def test_ingest_admitted():
    from l9_ops_mcp.memory_ops import ingest_episode
    from l9_ops_mcp.models import MemoryCandidate

    c = MemoryCandidate(
        body="Integration test: Graphiti is the L9 graph backend.",
        source_agent_id="test-agent",
        session_id="s-integration",
        group_ids=["session__s-integration"],
        semantic_score=0.95,
    )
    result = await ingest_episode(c)
    assert result["admitted"] is True


@pytest.mark.asyncio
async def test_ingest_default_group_accepted():
    """RG-01 live: the default ingest group (session__current) is accepted by graphiti-core."""
    from l9_ops_mcp.memory_ops import ingest_episode
    from l9_ops_mcp.models import MemoryCandidate

    c = MemoryCandidate(
        body="Integration test: default ingest group is graphiti-valid.",
        source_agent_id="test-agent",
        session_id="s-integration",
        semantic_score=0.95,
    )
    result = await ingest_episode(c)
    assert result["admitted"] is True


@pytest.mark.asyncio
async def test_hydrate_returns_bounded_readonly():
    from l9_ops_mcp.hydrator import hydrate

    p = await hydrate("integration test", "test-agent", 4000, "L2", "s-integration")
    assert p.readonly is True
    assert 0 <= p.budget_remaining_tokens <= 4000
    # RG-01/RG-04 live: every fact comes from an encoded L2 group and carries it.
    for tier in (p.context_slice.tier1_load_bearing, p.context_slice.tier2_examples):
        for fact in tier:
            assert fact.group_id in p.allowed_scopes


@pytest.mark.asyncio
async def test_low_score_quarantined():
    from l9_ops_mcp.memory_ops import ingest_episode
    from l9_ops_mcp.models import MemoryCandidate

    c = MemoryCandidate(
        body="xkzq noise",
        source_agent_id="test-agent",
        session_id="s-integration",
        semantic_score=0.05,
    )
    result = await ingest_episode(c)
    assert result["admitted"] is False
    assert "quarantine" in result["disposition"]


@pytest.mark.asyncio
async def test_invalidate_round_trip():
    """RG-06 live: ingest -> hydrate -> invalidate edge -> hydrate no longer serves it."""
    from l9_ops_mcp.hydrator import hydrate
    from l9_ops_mcp.memory_ops import ingest_episode
    from l9_ops_mcp.models import MemoryCandidate
    from l9_ops_mcp.server import memory_invalidate_fact

    c = MemoryCandidate(
        body="Integration round trip: the L9 invalidation probe uses Neo4j relationships.",
        source_agent_id="test-agent",
        session_id="s-invalidate",
        group_ids=["session__s-invalidate"],
        semantic_score=0.95,
    )
    await ingest_episode(c)
    before = await hydrate("L9 invalidation probe", "test-agent", 4000, "L5", "s-invalidate")
    facts = before.context_slice.tier1_load_bearing + before.context_slice.tier2_examples
    assert facts, "graphiti extracted no fact edges from the ingested episode"
    target = facts[0].uuid

    result = await memory_invalidate_fact(target, "integration round trip")
    assert result["invalidated"] == target

    missing = await memory_invalidate_fact("00000000-0000-0000-0000-000000000000", "x")
    assert missing["status"] == "not_found"

    after = await hydrate("L9 invalidation probe", "test-agent", 4000, "L5", "s-invalidate")
    served = {
        f.uuid
        for f in after.context_slice.tier1_load_bearing
        + after.context_slice.tier2_examples
        + after.context_slice.tier3_stakes
    }
    assert target not in served
