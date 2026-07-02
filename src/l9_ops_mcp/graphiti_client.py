"""L9 Graphiti client singleton.

Resolves U-M2 (memory_admission_kernel) and U-H2 (context_budget_kernel):
Graphiti + Neo4j is the L9 graph backend for allowed_scopes resolution and
durable memory. This is the ONLY module permitted to open a graph connection.
"""
from __future__ import annotations

import os
from functools import lru_cache

from graphiti_core import Graphiti

NEO4J_URI = os.getenv("L9_NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("L9_NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("L9_NEO4J_PASS", "l9_local_dev_pw")


@lru_cache(maxsize=1)
def _client() -> Graphiti:
    return Graphiti(NEO4J_URI, NEO4J_USER, NEO4J_PASS)


async def get_graphiti() -> Graphiti:
    """Return the process-wide Graphiti singleton, initializing indices once."""
    g = _client()
    if not getattr(g, "_l9_indices_built", False):
        await g.build_indices_and_constraints()
        g._l9_indices_built = True  # type: ignore[attr-defined]
    return g


async def close() -> None:
    g = _client()
    await g.close()
