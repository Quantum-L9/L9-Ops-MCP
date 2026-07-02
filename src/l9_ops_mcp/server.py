"""L9-Ops-MCP MCP server — 4 governed memory tools for Cursor, Claude, agents."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from .hydrator import hydrate
from .memory_ops import ingest_episode
from .models import MemoryCandidate

mcp = FastMCP(
    "l9-ops-mcp",
    instructions=(
        "L9 governed memory: use memory_get_budget_slice to read context, "
        "memory_ingest_episode to write, memory_query_context for search, "
        "memory_invalidate_fact to expire stale facts."
    ),
)


@mcp.tool()
async def memory_get_budget_slice(
    task_type: str,
    agent_id: str,
    token_budget: int,
    trust_level: str,
    session_id: str,
) -> dict:
    """Return a budget-bounded, read-only RuntimePayload for the given task.
    This is the ONLY way to inject graph context into an agent context window."""
    payload = await hydrate(task_type, agent_id, token_budget, trust_level, session_id)  # type: ignore[arg-type]
    return payload.model_dump(mode="json")


@mcp.tool()
async def memory_ingest_episode(
    body: str,
    source_agent_id: str,
    session_id: str,
    group_ids: list[str] | None = None,
    semantic_score: float = 1.0,
    trust_level: str = "L2",
) -> dict:
    """Write a durable memory episode through the 5-criteria admission gate.
    Low-quality or low-trust writes are quarantined, not silently admitted."""
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


@mcp.tool()
async def memory_query_context(
    query: str,
    group_ids: list[str] | None = None,
    limit: int = 10,
) -> dict:
    """Read-only graph search across sessions, agents, playbooks, decisions."""
    from .graphiti_client import get_graphiti
    g = await get_graphiti()
    hits = await g.search(query=query, group_ids=group_ids, num_results=limit)
    return {
        "facts": [
            {
                "fact":     h.fact,
                "uuid":     str(getattr(h, "uuid", "")),
                "valid_at": str(getattr(h, "valid_at", None)),
            }
            for h in hits
        ]
    }


@mcp.tool()
async def memory_invalidate_fact(entity_uuid: str, reason: str) -> dict:
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
