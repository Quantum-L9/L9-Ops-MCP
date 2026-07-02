"""Thin CLI so shell/cron paths can reach the graph tools without an MCP client.

Usage:
  python -m l9_ops_mcp.cli ingest '{"body": "...", ...}'
  python -m l9_ops_mcp.cli query  '{"query": "...", "limit": 10}'
"""
from __future__ import annotations

import asyncio
import json
import sys

from .memory_ops import ingest_episode
from .models import MemoryCandidate


async def _ingest(p: dict) -> dict:
    return await ingest_episode(MemoryCandidate(**p))


async def _query(p: dict) -> dict:
    from .graphiti_client import get_graphiti
    g = await get_graphiti()
    hits = await g.search(query=p["query"], group_ids=p.get("group_ids"),
                          num_results=p.get("limit", 10))
    return {"facts": [{"fact": h.fact} for h in hits]}


def main() -> None:
    cmd, payload = sys.argv[1], json.loads(sys.argv[2])
    fn = {"ingest": _ingest, "query": _query}[cmd]
    print(json.dumps(asyncio.run(fn(payload))))


if __name__ == "__main__":
    main()
