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
import sys
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .kernel_models import (
    KernelAuthorityError,
    KernelNotFoundError,
    KernelRequestInvalidError,
    KernelResolutionRequest,
    KernelSchemaInvalidError,
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
    """Return the process-cached resolver, loading it on first call.

    Cache-invalidation contract (execution contract §37):

    - The cache is safe as long as canonical kernel bytes and the
      retrieval index are immutable during the server's lifetime. A
      fresh process and a warm process produce identical resolutions
      for identical inputs (proved by the determinism test suite).
    - If ``L9_KERNEL_STRICT_INTEGRITY`` is set to a truthy value the
      registry re-verifies every canonical kernel's on-disk sha256
      against its cached record on every call. This defeats the cache
      for latency but guarantees zero staleness — useful for PE
      integrations that must detect a mid-process repo mutation.
    - Full cache invalidation on repo mutation is a Slice 2 PE-integration
      prerequisite; the current cache assumes an immutable repo checkout.
    """

    global _KERNEL_REGISTRY, _KERNEL_RESOLVER
    if _KERNEL_RESOLVER is None:
        _KERNEL_REGISTRY = KernelRegistry.load(_repo_root())
        _KERNEL_RESOLVER = KernelResolver(_KERNEL_REGISTRY)
    strict = os.getenv("L9_KERNEL_STRICT_INTEGRITY", "").lower() in {"1", "true", "yes", "on"}
    if strict and _KERNEL_REGISTRY is not None:
        _KERNEL_REGISTRY.verify_integrity()
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
    from .trust_ladder import validate_trust_level

    level = validate_trust_level(trust_level)  # raises before any graph access

    from .hydrator import hydrate

    payload = await hydrate(task_type, agent_id, token_budget, level, session_id)
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
    from .trust_ladder import SESSION_CURRENT

    c = MemoryCandidate(
        body=body,
        source_agent_id=source_agent_id,
        session_id=session_id,
        origin_timestamp=datetime.now(timezone.utc),
        group_ids=group_ids or [SESSION_CURRENT],
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


# Facts are RELATES_TO relationships between Entity nodes (graphiti-core
# EntityEdge); a node pattern such as (n {uuid: $uuid}) can never match one.
# invalid_at / expired_at follow graphiti's own invalidation semantics and are
# stored as datetimes; read paths exclude edges with invalid_at set.
_INVALIDATE_EDGE_CYPHER = """
MATCH (:Entity)-[e:RELATES_TO {uuid: $uuid}]->(:Entity)
SET e.invalid_at = $ts,
    e.expired_at = coalesce(e.expired_at, $ts),
    e.invalid_reason = $reason
RETURN e.uuid AS uuid
"""


@mcp.tool()  # type: ignore[untyped-decorator]
async def memory_invalidate_fact(entity_uuid: str, reason: str) -> dict[str, object]:
    """Mark a graph fact (RELATES_TO edge, by uuid) as invalid. Does not delete it.

    Returns ``{invalidated, reason, ts}`` when the edge was updated and
    ``{status: 'not_found', invalidated: None, uuid}`` when no fact edge has
    that uuid. Driver errors surface as tool errors."""
    from .graphiti_client import get_graphiti

    g = await get_graphiti()
    now = datetime.now(timezone.utc)
    records, _, _ = await g.driver.execute_query(
        _INVALIDATE_EDGE_CYPHER,
        uuid=entity_uuid,
        ts=now,
        reason=reason,
    )
    if not records:
        return {"status": "not_found", "invalidated": None, "uuid": entity_uuid}
    return {
        "status": "invalidated",
        "invalidated": entity_uuid,
        "reason": reason,
        "ts": now.isoformat(),
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
    authority, a bounded Tier-1 normative-context projection, the
    ``trust_level`` used to gate the resolution, and an aggregate
    ``resolution_digest`` that is stable across processes for the same
    repository state and request.

    Fails closed on: unknown profile, insufficient trust for a kernel's
    ring, deprecated / experimental kernel selection, unsatisfied
    requirement, dependency cycle, overload-budget exceeded, retrieval-index
    digest mismatch, malformed request, or any unexpected internal error
    while loading the registry. See ``src/l9_ops_mcp/kernel_models.py`` for
    the stable error-code taxonomy.

    Every failure path returns the ``{status: 'error', code, message}``
    envelope. Caller faults (bad input types, NaN/Inf floats) map to
    ``KERNEL_REQUEST_INVALID``. Repository-state faults while loading the
    registry (missing, unreadable or malformed index / schema / kernel) are
    mapped by ``kernel_registry`` to repository codes (``KERNEL_NOT_FOUND``,
    ``KERNEL_INDEX_ENTRY_MISSING``, ``KERNEL_SCHEMA_INVALID``); any other
    load-time fault is reported as ``KERNEL_NOT_FOUND`` (I/O) or
    ``KERNEL_SCHEMA_INVALID`` (data), never as a caller fault, so the MCP
    boundary never leaks a raw Python traceback to callers.

    This tool is normative authority. It does NOT read Graphiti, memory, or
    an LLM.
    """

    try:
        coerced_budget = _coerce_max_overload_weight(max_overload_weight)
        request = KernelResolutionRequest(
            profile=profile,
            consumer=consumer,
            objective=objective,
            trust_level=trust_level,
            max_overload_weight=coerced_budget,
            requested_kernel_ids=(),
            allow_experimental=bool(allow_experimental),
        )
    except KernelAuthorityError as exc:
        return exc.to_dict()
    except (TypeError, ValueError) as exc:
        return KernelRequestInvalidError(f"malformed kernel_resolve request: {exc}").to_dict()

    try:
        resolver = _get_resolver()
    except KernelAuthorityError as exc:
        return exc.to_dict()
    except OSError as exc:
        # Repository state could not be read (missing or unreadable index,
        # canonical kernel, or schema).
        return KernelNotFoundError(f"kernel authority load failed: {exc}").to_dict()
    except (TypeError, ValueError) as exc:
        # Malformed repository data surfaced outside the registry's own
        # mapping. This is a repository fault, not a caller fault.
        return KernelSchemaInvalidError(f"kernel authority load failed: {exc}").to_dict()

    try:
        resolution = resolver.resolve(request)
    except KernelAuthorityError as exc:
        return exc.to_dict()
    except (TypeError, ValueError) as exc:
        # Malformed input types that reached the domain layer despite the
        # coercion guard. Map to the stable request-invalid envelope.
        return KernelRequestInvalidError(f"malformed kernel_resolve request: {exc}").to_dict()

    payload = resolution.to_dict()
    payload["status"] = "ok"
    # Trust provenance: surface the gating trust_level at the top of the
    # response so PE consumers can persist it in Program Lock without
    # re-reading ``normalized_request``. This value is already part of the
    # digest via ``normalized_request``.
    payload["trust_level"] = request.trust_level
    return payload


def _coerce_max_overload_weight(value: object) -> float:
    """Coerce the max_overload_weight argument to a well-formed float.

    Accepts Python numbers and numeric strings (e.g. ``"6.0"``); rejects
    non-coercible types, NaN, and ±Inf with a stable
    :class:`KernelRequestInvalidError`. Called from inside the
    ``kernel_resolve`` try-block so the whole coercion feeds the same
    error envelope.
    """

    import math

    try:
        coerced = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise KernelRequestInvalidError(
            f"max_overload_weight must be a real number, got {value!r}: {exc}"
        ) from exc
    if math.isnan(coerced) or math.isinf(coerced):
        raise KernelRequestInvalidError(f"max_overload_weight must be finite, got {coerced!r}")
    return coerced


_LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


def _configure_http(host: str, port: int) -> None:
    """Apply streamable-HTTP settings to the module-level FastMCP instance.

    mcp 1.x ``FastMCP.run()`` accepts only ``transport`` (and ``mount_path``);
    host, port and path live in ``FastMCP.settings`` and are read when
    ``run_streamable_http_async`` builds the app, so setting them here takes
    effect. DNS-rebinding protection mirrors the FastMCP constructor: enabled
    for loopback hosts, left as constructed otherwise (the constructor's
    loopback default would reject every non-loopback Host header).
    """
    settings = mcp.settings
    settings.host = host
    settings.port = port
    settings.streamable_http_path = "/mcp"
    if host not in _LOOPBACK_HOSTS:
        settings.transport_security = None


def main() -> None:
    transport = os.getenv("L9_MCP_TRANSPORT", "stdio")
    if transport == "http":
        host = os.getenv("L9_MCP_HTTP_HOST", "127.0.0.1")
        raw_port = os.getenv("L9_MCP_HTTP_PORT", "7010")
        try:
            port = int(raw_port)
        except ValueError:
            sys.exit(f"L9_MCP_HTTP_PORT must be an integer port, got {raw_port!r}")
        _configure_http(host, port)
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
