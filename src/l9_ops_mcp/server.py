"""L9-Ops-MCP server — exposes the graph as MCP tools.

Makes mcp://l9-memory/session.update (multi-agent-routing playbook memory_persist
step) a real endpoint. All agent<->graph traffic flows through these tools only;
no raw graph access, no raw memory dumps (context_budget_kernel hard_bans).
"""
from __future__ import annotations

from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from .hydrator import hydrate
from .memory_ops import ingest_episode
from .models import MemoryCandidate, TrustLevel

mcp = FastMCP("l9-ops-mcp")


@mcp.tool()
async def memory_get_budget_slice(
    task_type: str,
    agent_id: str,
    token_budget: int,
    trust_level: str,
    session_id: str,
) -> dict:
    """Hydrator entrypoint: return a budget-bounded, policy-filtered RuntimePayload."""
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
    """Single durable write path (was mcp://l9-memory/session.update)."""
    candidate = MemoryCandidate(
        body=body,
        source_agent_id=source_agent_id,
        session_id=session_id,
        origin_timestamp=datetime.now(timezone.utc),
        group_ids=group_ids or ["session:current"],
        semantic_score=semantic_score,
        trust_level=trust_level,  # type: ignore[arg-type]
    )
    return await ingest_episode(candidate)


@mcp.tool()
async def memory_query_context(query: str, group_ids: list[str] | None = None,
                               limit: int = 10) -> dict:
    """Read-only relational query across sessions/agents/playbooks."""
    from .graphiti_client import get_graphiti
    g = await get_graphiti()
    hits = await g.search(query=query, group_ids=group_ids, num_results=limit)
    return {"facts": [{"fact": h.fact, "uuid": getattr(h, "uuid", ""),
                       "valid_at": str(getattr(h, "valid_at", None))} for h in hits]}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
