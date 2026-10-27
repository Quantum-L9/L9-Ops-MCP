"""Single durable write path, gated by the admission gate."""

from __future__ import annotations

from . import admission
from .graphiti_client import get_graphiti
from .models import MemoryCandidate
from .trust_ladder import SESSION_CURRENT, normalize_group_id


async def _dedup(body: str) -> bool:
    g = await get_graphiti()
    hits = await g.search(query=body[:256], num_results=1)
    return bool(hits and float(getattr(hits[0], "score", 0) or 0) >= 0.95)


async def ingest_episode(c: MemoryCandidate) -> dict[str, object]:
    target_group = normalize_group_id((c.group_ids or [SESSION_CURRENT])[0])
    ok, disp = await admission.evaluate(c, _dedup)
    if not ok:
        return {"admitted": False, "disposition": disp}
    g = await get_graphiti()
    await g.add_episode(
        name=f"{c.source_agent_id}:{c.session_id}",
        episode_body=c.body,
        source_description=f"L9/{c.source_agent_id}",
        reference_time=c.origin_timestamp,
        group_id=target_group,
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
