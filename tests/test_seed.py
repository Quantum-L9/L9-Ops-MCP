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
def fake_graph(monkeypatch: pytest.MonkeyPatch) -> _RecordingGraph:
    g = _RecordingGraph()

    async def _get() -> _RecordingGraph:
        return g

    monkeypatch.setattr(seed, "get_graphiti", _get)
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
