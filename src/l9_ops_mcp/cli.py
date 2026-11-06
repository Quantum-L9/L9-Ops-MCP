# >>> l9:meta >>>
# id: L9-Ops-MCP.source.src_l9_ops_mcp_cli__py
# title: cli
# artifact_type: source
# mcp_primitive: resource
# callable: false
# retrievable: true
# injectable: true
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: src/l9_ops_mcp/cli.py
# content_hash: a57cbf1c01ca8b8f449f6333e88d923b5d2cf105a803a812ad61a15bdcc36b72
# token_cost_estimate: 243
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
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
    from .graphiti_client import get_graphiti

    g = await get_graphiti()
    hits = await g.search(
        query=p["query"],
        group_ids=p.get("group_ids"),
        num_results=p.get("limit", 10),
    )
    return {"facts": [{"fact": h.fact} for h in hits]}


CMDS = {"ingest": _ingest, "query": _query}


def main() -> None:
    cmd, payload = sys.argv[1], json.loads(sys.argv[2])
    print(json.dumps(asyncio.run(CMDS[cmd](payload))))


if __name__ == "__main__":
    main()
