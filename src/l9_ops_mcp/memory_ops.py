# >>> l9:meta >>>
# id: L9-Ops-MCP.source.src_l9_ops_mcp_memory_ops__py
# title: memory ops
# artifact_type: source
# mcp_primitive: resource
# callable: false
# retrievable: true
# injectable: true
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: src/l9_ops_mcp/memory_ops.py
# content_hash: 90a9e6fab5e57eb6f36a16c238f132bbdcf141f1055cbddaf063b1966d399012
# token_cost_estimate: 283
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
"""Single durable write path, gated by the admission gate."""

from __future__ import annotations

from . import admission
from .graphiti_client import get_graphiti
from .models import MemoryCandidate


async def _dedup(body: str) -> bool:
    g = await get_graphiti()
    hits = await g.search(query=body[:256], num_results=1)
    return bool(hits and float(getattr(hits[0], "score", 0) or 0) >= 0.95)


async def ingest_episode(c: MemoryCandidate) -> dict[str, object]:
    ok, disp = await admission.evaluate(c, _dedup)
    if not ok:
        return {"admitted": False, "disposition": disp}
    g = await get_graphiti()
    await g.add_episode(
        name=f"{c.source_agent_id}:{c.session_id}",
        episode_body=c.body,
        source_description=f"L9/{c.source_agent_id}",
        reference_time=c.origin_timestamp,
        group_id=(c.group_ids or ["session:current"])[0],
    )
    return {
        "admitted": True,
        "disposition": "admit",
        "provenance": {
            "agent": c.source_agent_id,
            "session": c.session_id,
            "ts": c.origin_timestamp.isoformat(),
        },
    }
