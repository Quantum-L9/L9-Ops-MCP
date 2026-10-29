"""CLI shim — lets shell/cron call graph tools without an MCP client.
Usage: python -m l9_ops_mcp.cli ingest '{...}' | query '{...}'
"""

from __future__ import annotations

import asyncio
import json
import sys

from .memory_ops import ingest_episode
from .models import MemoryCandidate


async def _ingest(p: dict[str, object]) -> dict[str, object]:
    return await ingest_episode(MemoryCandidate.model_validate(p))


async def _query(p: dict[str, object]) -> dict[str, object]:
    """Same trust-scoped read path as the memory_query_context MCP tool."""
    from .hydrator import query

    missing = [k for k in ("query", "agent_id", "trust_level") if not p.get(k)]
    if missing:
        msg = f"query payload missing required field(s): {', '.join(missing)}"
        raise ValueError(msg)
    group_ids = p.get("group_ids")
    if group_ids is not None and not (
        isinstance(group_ids, list) and all(isinstance(g, str) for g in group_ids)
    ):
        msg = "group_ids must be a list of strings"
        raise ValueError(msg)
    limit = p.get("limit", 10)
    if not isinstance(limit, int):
        msg = "limit must be an integer"
        raise ValueError(msg)
    facts = await query(
        str(p["query"]),
        str(p["agent_id"]),
        str(p["trust_level"]),
        limit=limit,
        group_ids=group_ids,
    )
    return {"facts": facts}


CMDS = {"ingest": _ingest, "query": _query}


def main() -> None:
    cmd, payload = sys.argv[1], json.loads(sys.argv[2])
    try:
        result = asyncio.run(CMDS[cmd](payload))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
