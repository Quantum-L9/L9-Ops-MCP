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
    from datetime import datetime, timezone
    from l9_ops_mcp.memory_ops import ingest_episode
    from l9_ops_mcp.models import MemoryCandidate
    c = MemoryCandidate(
        body="Integration test: Graphiti is the L9 graph backend.",
        source_agent_id="test-agent",
        session_id="s-integration",
        group_ids=["session:s-integration"],
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
