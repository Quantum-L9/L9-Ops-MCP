"""L9 Graphiti singleton — the ONLY module that opens a graph connection.
Resolves U-H2 / U-M2 from context_budget_kernel + memory_admission_kernel.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal

from graphiti_core import Graphiti
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.llm_client import LLMConfig, OpenAIClient
from graphiti_core.search.search_config_recipes import EDGE_HYBRID_SEARCH_RRF

OPENAI_KEY_ENV = "L9_OPENAI_API_KEY"
_UPSTREAM_OPENAI_KEY_ENV = "OPENAI_API_KEY"


class GraphitiConfigError(RuntimeError):
    """Raised when the Graphiti client cannot be configured from the environment."""


def _uri() -> str:
    return os.getenv("L9_NEO4J_URI", "bolt://localhost:7687")


def _user() -> str:
    return os.getenv("L9_NEO4J_USER", "neo4j")


def _pass() -> str:
    return os.getenv("L9_NEO4J_PASS", "l9_local_dev_pw")


def _openai_key() -> str:
    """Return the OpenAI key for Graphiti's LLM, embedder and reranker clients.

    The documented variable is ``L9_OPENAI_API_KEY`` (.env.example and the
    client-config writers). graphiti-core's default clients only read
    ``OPENAI_API_KEY``, so the mapping is owned here; ``OPENAI_API_KEY`` is
    accepted as a fallback. An empty value counts as missing.
    """
    key = os.getenv(OPENAI_KEY_ENV) or os.getenv(_UPSTREAM_OPENAI_KEY_ENV)
    if not key:
        msg = (
            f"{OPENAI_KEY_ENV} is not set: Graphiti needs an OpenAI API key for entity "
            f"extraction, embeddings and reranking (set {OPENAI_KEY_ENV} in the MCP "
            "server environment)"
        )
        raise GraphitiConfigError(msg)
    return key


@lru_cache(maxsize=1)
def _client() -> Graphiti:
    key = _openai_key()
    return Graphiti(
        _uri(),
        _user(),
        _pass(),
        llm_client=OpenAIClient(config=LLMConfig(api_key=key)),
        embedder=OpenAIEmbedder(config=OpenAIEmbedderConfig(api_key=key)),
        cross_encoder=OpenAIRerankerClient(config=LLMConfig(api_key=key)),
    )


async def get_graphiti() -> Graphiti:
    g = _client()
    if not getattr(g, "_l9_indices_built", False):
        await g.build_indices_and_constraints()
        setattr(g, "_l9_indices_built", True)
    return g


async def close() -> None:
    await _client().close()


RelevanceSignal = Literal["rrf", "ordinal"]


@dataclass(frozen=True)
class ScoredEdges:
    """Edges in relevance order with one score per edge and the signal used."""

    edges: list[Any]
    scores: list[float]
    signal: RelevanceSignal


async def search_edges(
    g: Graphiti,
    query: str,
    group_ids: list[str] | None,
    limit: int,
) -> ScoredEdges:
    """Hybrid edge search returning real relevance scores.

    ``Graphiti.search()`` returns bare ``EntityEdge`` objects (which carry no
    score) and mutates the shared ``EDGE_HYBRID_SEARCH_RRF`` recipe's limit.
    This uses ``Graphiti.search_()`` with a private copy of the same RRF recipe
    and takes the reciprocal-rank-fusion scores from
    ``SearchResults.edge_reranker_scores`` (deterministic; no LLM call). If the
    scores are unavailable or misaligned, it falls back explicitly to an
    ordinal score derived from rank (``signal="ordinal"``).
    """
    config = EDGE_HYBRID_SEARCH_RRF.model_copy(update={"limit": limit})
    results = await g.search_(query=query, config=config, group_ids=group_ids)
    edges = list(results.edges)
    scores = [float(x) for x in results.edge_reranker_scores]
    if edges and len(scores) == len(edges):
        return ScoredEdges(edges=edges, scores=scores, signal="rrf")
    n = len(edges)
    return ScoredEdges(edges=edges, scores=[(n - i) / n for i in range(n)], signal="ordinal")
