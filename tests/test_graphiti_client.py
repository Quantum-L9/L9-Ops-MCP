"""Graphiti client construction (RG-14). Constructs the real client; no I/O happens
at construction (the Neo4j async driver connects lazily)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

import l9_ops_mcp.graphiti_client as gc


@pytest.fixture(autouse=True)
def _fresh_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("L9_OPENAI_API_KEY", raising=False)
    gc._client.cache_clear()
    yield
    gc._client.cache_clear()


def test_documented_l9_key_constructs_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("L9_OPENAI_API_KEY", "sk-l9-test")
    g = gc._client()
    assert g.llm_client.client.api_key == "sk-l9-test"
    assert g.embedder.client.api_key == "sk-l9-test"
    assert g.cross_encoder.client.api_key == "sk-l9-test"


def test_missing_key_names_the_variable() -> None:
    with pytest.raises(gc.GraphitiConfigError, match="L9_OPENAI_API_KEY"):
        gc._client()


def test_empty_l9_key_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    # The config writers emit L9_OPENAI_API_KEY="" when the operator has none.
    monkeypatch.setenv("L9_OPENAI_API_KEY", "")
    with pytest.raises(gc.GraphitiConfigError, match="L9_OPENAI_API_KEY"):
        gc._client()


def test_upstream_variable_still_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-upstream")
    g = gc._client()
    assert g.embedder.client.api_key == "sk-upstream"
