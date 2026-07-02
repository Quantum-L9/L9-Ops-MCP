"""Unit tests for the admission gate. No Neo4j required."""
import asyncio
import pytest
from l9_ops_mcp.admission import evaluate
from l9_ops_mcp.models import MemoryCandidate


async def _no_dup(_body: str) -> bool:
    return False


def test_quarantines_low_score(tmp_path, monkeypatch):
    import l9_ops_mcp.admission as adm
    monkeypatch.setattr(adm, "LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(adm, "QUARANTINE", tmp_path / "q")
    c = MemoryCandidate(
        body="noise", source_agent_id="a",
        session_id="s", semantic_score=0.10,
    )
    ok, disp = asyncio.run(evaluate(c, _no_dup))
    assert not ok
    assert "quarantine" in disp


def test_blocks_low_trust(tmp_path, monkeypatch):
    import l9_ops_mcp.admission as adm
    monkeypatch.setattr(adm, "LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(adm, "QUARANTINE", tmp_path / "q")
    c = MemoryCandidate(
        body="important decision", source_agent_id="a",
        session_id="s", semantic_score=0.90, trust_level="L0",
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
        source_agent_id="a", session_id="s",
        semantic_score=0.90, trust_level="L2",
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
        body="duplicate fact", source_agent_id="a",
        session_id="s", semantic_score=0.90, trust_level="L2",
    )
    ok, disp = asyncio.run(evaluate(c, is_dup))
    assert not ok
    assert "dedup" in disp
