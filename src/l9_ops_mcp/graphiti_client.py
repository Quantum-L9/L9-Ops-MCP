# >>> l9:meta >>>
# id: L9-Ops-MCP.source.src_l9_ops_mcp_graphiti_client__py
# title: graphiti client
# artifact_type: source
# mcp_primitive: resource
# callable: false
# retrievable: true
# injectable: true
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: src/l9_ops_mcp/graphiti_client.py
# content_hash: cd698e83ec5e5eda969f50cc152bac2397b7dcfd0626a0ff4cfbdc24a900a039
# token_cost_estimate: 218
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
"""L9 Graphiti singleton — the ONLY module that opens a graph connection.
Resolves U-H2 / U-M2 from context_budget_kernel + memory_admission_kernel.
"""

from __future__ import annotations

import os
from functools import lru_cache

from graphiti_core import Graphiti


def _uri() -> str:
    return os.getenv("L9_NEO4J_URI", "bolt://localhost:7687")


def _user() -> str:
    return os.getenv("L9_NEO4J_USER", "neo4j")


def _pass() -> str:
    return os.getenv("L9_NEO4J_PASS", "l9_local_dev_pw")


@lru_cache(maxsize=1)
def _client() -> Graphiti:
    return Graphiti(_uri(), _user(), _pass())


async def get_graphiti() -> Graphiti:
    g = _client()
    if not getattr(g, "_l9_indices_built", False):
        await g.build_indices_and_constraints()
        setattr(g, "_l9_indices_built", True)
    return g


async def close() -> None:
    await _client().close()
