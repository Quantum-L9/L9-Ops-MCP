"""Durable memory ingest — the single write path, gated by admission.

Wraps graphiti.add_episode() behind the memory_admission_kernel gate so the
durable_memory_single_path invariant is enforced at runtime.
"""
from __future__ import annotations

from . import admission
from .graphiti_client import get_graphiti
from .models import MemoryCandidate


async def _dedup_check(body: str) -> bool:
    g = await get_graphiti()
    hits = await g.search(query=body[:256], num_results=1)
    return bool(hits and getattr(hits[0], "score", 0.0) >= 0.95)


async def ingest_episode(candidate: MemoryCandidate) -> dict:
    admitted, disposition = await admission.evaluate(candidate, _dedup_check)
    if not admitted:
        return {"admitted": False, "disposition": disposition}

    g = await get_graphiti()
    await g.add_episode(
        name=f"{candidate.source_agent_id}:{candidate.session_id}",
        episode_body=candidate.body,
        source_description=f"L9 agent {candidate.source_agent_id}",
        reference_time=candidate.origin_timestamp,
        group_id=(candidate.group_ids or ["session:current"])[0],
    )
    return {"admitted": True, "disposition": "admit",
            "provenance": {"agent": candidate.source_agent_id,
                           "session": candidate.session_id,
                           "ts": candidate.origin_timestamp.isoformat()}}
