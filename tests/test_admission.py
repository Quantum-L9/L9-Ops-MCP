import asyncio

from l9_ops_mcp.admission import evaluate
from l9_ops_mcp.models import MemoryCandidate


async def _no_dup(_body):
    return False


def test_low_relevance_quarantined(tmp_path, monkeypatch):
    import l9_ops_mcp.admission as adm
    monkeypatch.setattr(adm, "LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(adm, "QUARANTINE", tmp_path / "q")
    c = MemoryCandidate(body="noise", source_agent_id="a", session_id="s",
                        semantic_score=0.10)
    admitted, disp = asyncio.run(evaluate(c, _no_dup))
    assert not admitted and disp == "quarantine:relevance"


def test_valid_candidate_admitted(tmp_path, monkeypatch):
    import l9_ops_mcp.admission as adm
    monkeypatch.setattr(adm, "LOG", tmp_path / "log.jsonl")
    c = MemoryCandidate(body="real decision", source_agent_id="a", session_id="s",
                        semantic_score=0.90, trust_level="L2")
    admitted, disp = asyncio.run(evaluate(c, _no_dup))
    assert admitted and disp == "admit"
