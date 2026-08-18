"""L9-Ops-MCP MCP server.

Two planes are exposed:

- **Governed memory** (existing): ``memory_get_budget_slice``,
  ``memory_ingest_episode``, ``memory_query_context``,
  ``memory_invalidate_fact``. These are Graphiti-backed and are advisory /
  historical context.
- **Canonical kernel authority** (Slice 1): ``kernel_resolve``. This is
  the deterministic normative-authority plane. It does not consult
  Graphiti, an LLM, or memory. It answers the question
  \"What normative kernel authority applies to this execution profile?\"
  Memory search cannot substitute for it, and it cannot substitute for
  Program Lock / PE execution authority.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .kernel_models import (
    KernelAuthorityError,
    KernelResolutionRequest,
)
from .kernel_registry import KernelRegistry
from .kernel_resolver import KernelResolver

# Memory-plane imports (hydrator, memory_ops, models) are performed lazily
# inside each memory tool. This preserves the kernel authority plane's
# offline / no-network / no-Graphiti guarantee (execution contract §50): the
# kernel_resolve tool must remain callable without graphiti_core, neo4j, or
# tiktoken installed.

mcp = FastMCP(
    "l9-ops-mcp",
    instructions=(
        "L9-Ops-MCP exposes two planes. "
        "Governed memory (advisory / historical): use memory_get_budget_slice "
        "to read context, memory_ingest_episode to write, memory_query_context "
        "for search, memory_invalidate_fact to expire stale facts. "
        "Canonical kernel authority (normative): use kernel_resolve to obtain "
        "a deterministic kernel-authority resolution for a declared execution "
        "profile. Kernel resolution never consults Graphiti or an LLM."
    ),
)


_KERNEL_REGISTRY: KernelRegistry | None = None
_KERNEL_RESOLVER: KernelResolver | None = None


def _repo_root() -> Path:
    override = os.getenv("L9_OPS_MCP_REPO_ROOT")
    if override:
        return Path(override)
    # Package lives at <repo>/src/l9_ops_mcp/server.py; repo root is 3 parents up.
    return Path(__file__).resolve().parents[2]


def _get_resolver() -> KernelResolver:
    global _KERNEL_REGISTRY, _KERNEL_RESOLVER
    if _KERNEL_RESOLVER is None:
        _KERNEL_REGISTRY = KernelRegistry.load(_repo_root())
        _KERNEL_RESOLVER = KernelResolver(_KERNEL_REGISTRY)
    return _KERNEL_RESOLVER


@mcp.tool()  # type: ignore[untyped-decorator]
async def memory_get_budget_slice(
    task_type: str,
    agent_id: str,
    token_budget: int,
    trust_level: str,
    session_id: str,
) -> dict[str, object]:
    """Return a budget-bounded, read-only RuntimePayload for the given task.
    This is the ONLY way to inject graph context into an agent context window."""
    from .hydrator import hydrate

    payload = await hydrate(task_type, agent_id, token_budget, trust_level, session_id)  # type: ignore[arg-type]
    return payload.model_dump(mode="json")


@mcp.tool()  # type: ignore[untyped-decorator]
async def memory_ingest_episode(
    body: str,
    source_agent_id: str,
    session_id: str,
    group_ids: list[str] | None = None,
    semantic_score: float = 1.0,
    trust_level: str = "L2",
) -> dict[str, object]:
    """Write a durable memory episode through the 5-criteria admission gate.
    Low-quality or low-trust writes are quarantined, not silently admitted."""
    from .memory_ops import ingest_episode
    from .models import MemoryCandidate

    c = MemoryCandidate(
        body=body,
        source_agent_id=source_agent_id,
        session_id=session_id,
        origin_timestamp=datetime.now(timezone.utc),
        group_ids=group_ids or ["session:current"],
        semantic_score=semantic_score,
        trust_level=trust_level,  # type: ignore[arg-type]
    )
    return await ingest_episode(c)


@mcp.tool()  # type: ignore[untyped-decorator]
async def memory_query_context(
    query: str,
    group_ids: list[str] | None = None,
    limit: int = 10,
) -> dict[str, object]:
    """Read-only graph search across sessions, agents, playbooks, decisions."""
    from .graphiti_client import get_graphiti

    g = await get_graphiti()
    hits = await g.search(query=query, group_ids=group_ids, num_results=limit)
    return {
        "facts": [
            {
                "fact": h.fact,
                "uuid": str(getattr(h, "uuid", "")),
                "valid_at": str(getattr(h, "valid_at", None)),
            }
            for h in hits
        ]
    }


@mcp.tool()  # type: ignore[untyped-decorator]
async def memory_invalidate_fact(entity_uuid: str, reason: str) -> dict[str, object]:
    """Mark a graph fact as invalid (temporal expiry). Does not delete the node."""
    from .graphiti_client import get_graphiti

    g = await get_graphiti()
    await g.driver.execute_query(
        "MATCH (n {uuid: $uuid}) SET n.invalid_at = $ts, n.invalid_reason = $reason",
        uuid=entity_uuid,
        ts=datetime.now(timezone.utc).isoformat(),
        reason=reason,
    )
    return {
        "invalidated": entity_uuid,
        "reason": reason,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()  # type: ignore[untyped-decorator]
async def kernel_resolve(
    profile: str,
    consumer: str,
    objective: str,
    trust_level: str,
    max_overload_weight: float,
    allow_experimental: bool = False,
) -> dict[str, object]:
    """Resolve deterministic canonical kernel authority for an execution profile.

    Returns the exact selected kernel set, provenance sufficient to re-pin
    authority, a bounded Tier-1 normative-context projection, and an
    aggregate ``resolution_digest`` that is stable across processes for the
    same repository state and request.

    Fails closed on: unknown profile, insufficient trust for a kernel's
    ring, deprecated / experimental kernel selection, unsatisfied
    requirement, dependency cycle, overload-budget exceeded, retrieval-index
    digest mismatch, or malformed request. See
    ``src/l9_ops_mcp/kernel_models.py`` for the stable error-code taxonomy.

    This tool is normative authority. It does NOT read Graphiti, memory, or
    an LLM.
    """

    try:
        request = KernelResolutionRequest(
            profile=profile,
            consumer=consumer,
            objective=objective,
            trust_level=trust_level,
            max_overload_weight=float(max_overload_weight),
            requested_kernel_ids=(),
            allow_experimental=bool(allow_experimental),
        )
        resolver = _get_resolver()
        resolution = resolver.resolve(request)
    except KernelAuthorityError as exc:
        return exc.to_dict()

    payload = resolution.to_dict()
    payload["status"] = "ok"
    return payload


def main() -> None:
    transport = os.getenv("L9_MCP_TRANSPORT", "stdio")
    if transport == "http":
        host = os.getenv("L9_MCP_HTTP_HOST", "127.0.0.1")
        port = int(os.getenv("L9_MCP_HTTP_PORT", "7010"))
        mcp.run(transport="streamable-http", host=host, port=port, path="/mcp")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
