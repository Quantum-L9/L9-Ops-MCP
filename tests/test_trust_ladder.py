"""Unit tests for trust-ladder scope resolution."""

import asyncio
from typing import Any

import pytest
from graphiti_core.errors import GroupIdValidationError
from graphiti_core.helpers import validate_group_ids
from graphiti_core.search.search_config import SearchResults

from l9_ops_mcp.trust_ladder import allowed_scopes, normalize_group_id


def test_l0_empty():
    assert allowed_scopes("any", "L0") == []


def test_l2_resolves_self():
    scopes = allowed_scopes("orchestrator", "L2")
    assert "agent__orchestrator" in scopes
    assert "global__decisions" not in scopes


def test_l4_includes_decisions():
    assert "global__decisions" in allowed_scopes("planner", "L4")


def test_l5_full_graph():
    assert allowed_scopes("root", "L5") == ["*"]


def test_unknown_level_empty():
    assert allowed_scopes("x", "L99") == []


def test_scope_membership_per_level_unchanged():
    assert allowed_scopes("a", "L1") == ["global__conventions"]
    assert allowed_scopes("a", "L2") == ["global__conventions", "agent__a", "session__current"]
    assert allowed_scopes("a", "L3") == [
        "global__conventions",
        "agent__a",
        "session__current",
        "playbook__history",
    ]
    assert allowed_scopes("a", "L4") == [
        "global__conventions",
        "agent__a",
        "session__current",
        "playbook__history",
        "global__decisions",
    ]


# --- RG-01: every emitted group id is accepted by the installed graphiti-core ---


@pytest.mark.parametrize("level", ["L1", "L2", "L3", "L4"])
@pytest.mark.parametrize("agent_id", ["orchestrator", "test-agent", "claude.code/desktop", "a b"])
def test_allowed_scopes_pass_graphiti_validation(level: str, agent_id: str) -> None:
    scopes = allowed_scopes(agent_id, level)
    assert scopes
    validate_group_ids(scopes)  # raises GroupIdValidationError on failure


def test_distinct_illegal_agent_ids_do_not_collide() -> None:
    a = allowed_scopes("team/a", "L2")[1]
    b = allowed_scopes("team.a", "L2")[1]
    assert a != b
    validate_group_ids([a, b])


def test_normalize_accepts_legacy_colon_form() -> None:
    assert normalize_group_id("session:s-integration") == "session__s-integration"
    assert normalize_group_id("global:decisions") == "global__decisions"
    assert normalize_group_id("session__current") == "session__current"
    validate_group_ids([normalize_group_id("agent:x.y")])


def test_normalize_rejects_unencodable_input() -> None:
    with pytest.raises(ValueError):
        normalize_group_id("bad id with spaces")
    with pytest.raises(ValueError):
        normalize_group_id("")


class _RecordingGraph:
    def __init__(self) -> None:
        self.episodes: list[dict[str, Any]] = []

    async def search(self, **kwargs: Any) -> list[Any]:
        return []

    async def search_(self, **kwargs: Any) -> SearchResults:
        validate_group_ids(kwargs.get("group_ids"))  # what graphiti-core enforces on read
        return SearchResults()

    async def add_episode(self, **kwargs: Any) -> None:
        validate_group_ids([kwargs["group_id"]])  # what graphiti-core enforces on write
        self.episodes.append(kwargs)


def _patch_graph(monkeypatch: pytest.MonkeyPatch, module: Any) -> _RecordingGraph:
    g = _RecordingGraph()

    async def _get() -> _RecordingGraph:
        return g

    monkeypatch.setattr(module, "get_graphiti", _get)
    return g


def test_default_ingest_group_is_valid(tmp_path, monkeypatch) -> None:
    import l9_ops_mcp.admission as adm
    import l9_ops_mcp.memory_ops as memory_ops
    from l9_ops_mcp.models import MemoryCandidate

    monkeypatch.setattr(adm, "LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(adm, "QUARANTINE", tmp_path / "q")
    g = _patch_graph(monkeypatch, memory_ops)
    c = MemoryCandidate(
        body="a durable fact", source_agent_id="a", session_id="s", semantic_score=0.9
    )
    result = asyncio.run(memory_ops.ingest_episode(c))
    assert result["admitted"] is True
    assert g.episodes[0]["group_id"] == "session__current"


def test_mcp_ingest_default_group_is_valid(tmp_path, monkeypatch) -> None:
    import l9_ops_mcp.admission as adm
    import l9_ops_mcp.memory_ops as memory_ops
    import l9_ops_mcp.server as server

    monkeypatch.setattr(adm, "LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(adm, "QUARANTINE", tmp_path / "q")
    g = _patch_graph(monkeypatch, memory_ops)
    asyncio.run(
        server.memory_ingest_episode(
            body="another durable fact", source_agent_id="a", session_id="s"
        )
    )
    assert g.episodes[0]["group_id"] == "session__current"


def test_legacy_colon_group_input_is_encoded_on_ingest(tmp_path, monkeypatch) -> None:
    import l9_ops_mcp.admission as adm
    import l9_ops_mcp.memory_ops as memory_ops
    from l9_ops_mcp.models import MemoryCandidate

    monkeypatch.setattr(adm, "LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(adm, "QUARANTINE", tmp_path / "q")
    g = _patch_graph(monkeypatch, memory_ops)
    c = MemoryCandidate(
        body="fact",
        source_agent_id="a",
        session_id="s",
        group_ids=["session:s-integration"],
        semantic_score=0.9,
    )
    asyncio.run(memory_ops.ingest_episode(c))
    assert g.episodes[0]["group_id"] == "session__s-integration"


def test_seed_group_is_valid(tmp_path, monkeypatch) -> None:
    import l9_ops_mcp.admission as adm
    import l9_ops_mcp.memory_ops as memory_ops
    import l9_ops_mcp.seed as seed

    monkeypatch.setattr(adm, "LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(adm, "QUARANTINE", tmp_path / "q")
    g = _patch_graph(monkeypatch, memory_ops)
    law = tmp_path / "CANONICAL_LAW.md"
    law.write_text("# Section one\n" + "x" * 80 + "\n", encoding="utf-8")
    try:
        asyncio.run(seed.seed(law))
    except GroupIdValidationError as exc:  # pragma: no cover - failure path
        pytest.fail(f"seed group id rejected by graphiti-core: {exc}")
    assert g.episodes
    assert {e["group_id"] for e in g.episodes} == {"global__decisions"}
