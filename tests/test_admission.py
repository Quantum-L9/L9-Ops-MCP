"""Unit tests for the admission gate. No Neo4j required."""

import asyncio
import json
from datetime import datetime, timezone

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


# --- RG-08: quarantine uniqueness, confinement, and logging ---


def _low(session_id: str, body: str, ts: datetime) -> MemoryCandidate:
    return MemoryCandidate(
        body=body,
        source_agent_id="a",
        session_id=session_id,
        origin_timestamp=ts,
        semantic_score=0.1,
    )


def test_quarantine_keeps_same_second_candidates_and_confines_paths(tmp_path, monkeypatch):
    import l9_ops_mcp.admission as adm

    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    log = work / "logs" / "log.jsonl"
    q = work / "memory_quarantine"
    monkeypatch.setattr(adm, "LOG", log)
    monkeypatch.setattr(adm, "QUARANTINE", q)
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)

    results = [
        asyncio.run(evaluate(_low("s", "first candidate", ts), _no_dup)),
        asyncio.run(evaluate(_low("s", "second candidate", ts), _no_dup)),
        asyncio.run(evaluate(_low("../x", "escape attempt", ts), _no_dup)),
        asyncio.run(evaluate(_low("a/b", "nested attempt", ts), _no_dup)),
    ]
    assert results == [(False, "quarantine:relevance")] * 4

    files = sorted(q.glob("*.json"))
    assert len(files) == 4
    bodies = {json.loads(f.read_text())["body"] for f in files}
    assert bodies == {"first candidate", "second candidate", "escape attempt", "nested attempt"}
    # nothing written outside memory_quarantine/
    written = {p for p in tmp_path.rglob("*") if p.is_file()}
    assert written == set(files) | {log}
    for f in files:
        assert f.resolve().parent == q.resolve()

    lines = [json.loads(line) for line in log.read_text().splitlines()]
    assert len(lines) == 4
    assert [line["disposition"] for line in lines] == ["quarantine"] * 4
    assert {line["session"] for line in lines} == {"s", "../x", "a/b"}


def test_quarantine_write_failure_is_logged_and_surfaced(tmp_path, monkeypatch):
    import l9_ops_mcp.admission as adm

    log = tmp_path / "log.jsonl"
    blocker = tmp_path / "q"
    blocker.write_text("not a directory")  # mkdir/write under it fails
    monkeypatch.setattr(adm, "LOG", log)
    monkeypatch.setattr(adm, "QUARANTINE", blocker)
    c = _low("s", "must not vanish", datetime(2026, 1, 1, tzinfo=timezone.utc))
    with pytest.raises(adm.QuarantineWriteError):
        asyncio.run(evaluate(c, _no_dup))
    lines = [json.loads(line) for line in log.read_text().splitlines()]
    assert lines[0]["disposition"] == "quarantine"
    assert lines[-1]["disposition"] == "quarantine_write_failed"
    assert lines[-1]["candidate"]["body"] == "must not vanish"
    assert lines[-1]["error"]
