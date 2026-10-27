"""Seeder tests (RG-15 location resolution). Fake graph; no Neo4j."""

from __future__ import annotations

import asyncio
import pathlib
import sys
from typing import Any

import pytest

import l9_ops_mcp.seed as seed

REPO_ROOT = pathlib.Path(seed.__file__).resolve().parents[2]


class _RecordingGraph:
    def __init__(self) -> None:
        self.episodes: list[dict[str, Any]] = []

    async def search(self, **kwargs: Any) -> list[Any]:
        return []

    async def search_(self, **kwargs: Any) -> Any:
        from graphiti_core.search.search_config import SearchResults

        return SearchResults()

    async def add_episode(self, **kwargs: Any) -> None:
        self.episodes.append(kwargs)


@pytest.fixture
def no_checkout(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("CG_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)
    return home


@pytest.fixture
def fake_graph(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> _RecordingGraph:
    import l9_ops_mcp.admission as adm
    import l9_ops_mcp.memory_ops as memory_ops

    monkeypatch.setattr(adm, "LOG", tmp_path / "admission.jsonl")
    monkeypatch.setattr(adm, "QUARANTINE", tmp_path / "quarantine")
    g = _RecordingGraph()

    async def _get() -> _RecordingGraph:
        return g

    monkeypatch.setattr(memory_ops, "get_graphiti", _get)
    return g


def test_candidates_are_documented_locations_only(no_checkout: pathlib.Path) -> None:
    assert seed._candidates() == [
        no_checkout / ".cursor-governance" / "CANONICAL_LAW.md",
        REPO_ROOT / "Cursor-Governance" / "CANONICAL_LAW.md",
    ]


def test_cg_root_takes_precedence(no_checkout: pathlib.Path, monkeypatch) -> None:
    monkeypatch.setenv("CG_ROOT", "/opt/cg")
    assert seed._candidates()[0] == pathlib.Path("/opt/cg") / "CANONICAL_LAW.md"


def test_missing_checkout_names_locations_and_exits_nonzero(
    no_checkout: pathlib.Path, monkeypatch, capsys, fake_graph: _RecordingGraph
) -> None:
    # cwd holds a CANONICAL_LAW.md: an unset CG_ROOT must not resolve to it.
    (pathlib.Path.cwd() / "CANONICAL_LAW.md").write_text("# x\n" + "y" * 80, encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["l9-seed"])
    with pytest.raises(SystemExit) as exc:
        seed.main()
    assert exc.value.code not in (0, None)
    err = capsys.readouterr().err
    assert str(no_checkout / ".cursor-governance" / "CANONICAL_LAW.md") in err
    assert str(REPO_ROOT / "Cursor-Governance" / "CANONICAL_LAW.md") in err
    assert "CG_ROOT" in err
    assert fake_graph.episodes == []


def test_valid_cg_root_is_used(
    tmp_path: pathlib.Path, no_checkout: pathlib.Path, monkeypatch, fake_graph: _RecordingGraph
) -> None:
    cg = tmp_path / "cg"
    cg.mkdir()
    (cg / "CANONICAL_LAW.md").write_text("# Law\n" + "z" * 80 + "\n", encoding="utf-8")
    monkeypatch.setenv("CG_ROOT", str(cg))
    assert seed._find() == cg / "CANONICAL_LAW.md"
    asyncio.run(seed.seed())
    assert fake_graph.episodes


# --- RG-11 (D-04 A): seeding goes through the admission gate ---------------


@pytest.fixture
def admitted_graph(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    import l9_ops_mcp.admission as adm
    import l9_ops_mcp.memory_ops as memory_ops

    log = tmp_path / "admission.jsonl"
    monkeypatch.setattr(adm, "LOG", log)
    monkeypatch.setattr(adm, "QUARANTINE", tmp_path / "quarantine")
    g = _RecordingGraph()

    async def _get() -> _RecordingGraph:
        return g

    monkeypatch.setattr(memory_ops, "get_graphiti", _get)
    return g, log


def _law(tmp_path: pathlib.Path, sections: int) -> pathlib.Path:
    law = tmp_path / "CANONICAL_LAW.md"
    law.write_text(
        "".join(f"## Section {i}\n" + f"rule {i} " * 20 + "\n" for i in range(sections)),
        encoding="utf-8",
    )
    return law


def test_seeded_writes_are_admitted_by_the_gate(tmp_path: pathlib.Path, admitted_graph) -> None:
    import json

    g, log = admitted_graph
    summary = asyncio.run(seed.seed(_law(tmp_path, 3)))
    assert summary["admitted"] == 3
    lines = [json.loads(line) for line in log.read_text().splitlines()]
    assert [line["disposition"] for line in lines] == ["admit"] * 3
    assert {line["agent"] for line in lines} == {seed.SEED_AGENT_ID}
    assert {e["group_id"] for e in g.episodes} == {"global__decisions"}
    assert len(g.episodes) == 3


def test_rejected_chunk_exits_nonzero_with_counts(
    tmp_path: pathlib.Path, admitted_graph, monkeypatch, capsys
) -> None:
    import l9_ops_mcp.memory_ops as memory_ops

    real = memory_ops.ingest_episode
    calls = {"n": 0}

    async def flaky(c):
        calls["n"] += 1
        if calls["n"] == 2:
            return {"admitted": False, "disposition": "block:provenance"}
        return await real(c)

    monkeypatch.setattr(seed, "ingest_episode", flaky)
    monkeypatch.setattr(sys, "argv", ["l9-seed", "--file", str(_law(tmp_path, 3))])
    with pytest.raises(SystemExit) as exc:
        seed.main()
    assert exc.value.code not in (0, None)
    err = capsys.readouterr().err
    assert "2 of 3" in err
    assert "block:provenance" in err
