# >>> l9:meta >>>
# id: L9-Ops-MCP.test.tests_test_admission__py
# title: test admission
# artifact_type: test
# mcp_primitive: none
# callable: false
# retrievable: false
# injectable: false
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: tests/test_admission.py
# content_hash: 1ed6345943d832789f412d38a6a1887bcf7abc1241127c91bce947fea1fa9874
# token_cost_estimate: 542
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
"""Unit tests for the admission gate. No Neo4j required."""

import asyncio
from l9_ops_mcp.admission import evaluate
from l9_ops_mcp.models import MemoryCandidate


async def _no_dup(_body: str) -> bool:
    return False


def test_quarantines_low_score(tmp_path, monkeypatch):
    import l9_ops_mcp.admission as adm

    monkeypatch.setattr(adm, "LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(adm, "QUARANTINE", tmp_path / "q")
    c = MemoryCandidate(
        body="noise",
        source_agent_id="a",
        session_id="s",
        semantic_score=0.10,
    )
    ok, disp = asyncio.run(evaluate(c, _no_dup))
    assert not ok
    assert "quarantine" in disp


def test_blocks_low_trust(tmp_path, monkeypatch):
    import l9_ops_mcp.admission as adm

    monkeypatch.setattr(adm, "LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(adm, "QUARANTINE", tmp_path / "q")
    c = MemoryCandidate(
        body="important decision",
        source_agent_id="a",
        session_id="s",
        semantic_score=0.90,
        trust_level="L0",
    )
    ok, disp = asyncio.run(evaluate(c, _no_dup))
    assert not ok
    assert "trust" in disp


def test_admits_valid(tmp_path, monkeypatch):
    import l9_ops_mcp.admission as adm

    monkeypatch.setattr(adm, "LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(adm, "QUARANTINE", tmp_path / "q")
    c = MemoryCandidate(
        body="real architectural decision",
        source_agent_id="a",
        session_id="s",
        semantic_score=0.90,
        trust_level="L2",
    )
    ok, disp = asyncio.run(evaluate(c, _no_dup))
    assert ok
    assert disp == "admit"


def test_blocks_dedup(tmp_path, monkeypatch):
    import l9_ops_mcp.admission as adm

    monkeypatch.setattr(adm, "LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(adm, "QUARANTINE", tmp_path / "q")

    async def is_dup(_body: str) -> bool:
        return True

    c = MemoryCandidate(
        body="duplicate fact",
        source_agent_id="a",
        session_id="s",
        semantic_score=0.90,
        trust_level="L2",
    )
    ok, disp = asyncio.run(evaluate(c, is_dup))
    assert not ok
    assert "dedup" in disp
