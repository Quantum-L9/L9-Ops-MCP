"""Single durable write path, gated by the admission gate."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from . import admission
from .graphiti_client import get_graphiti, search_edges
from .models import MemoryCandidate
from .trust_ladder import SESSION_CURRENT, normalize_group_id


_DEDUP_CANDIDATES = 10


def _normalize_fact(text: str) -> str:
    """Normalization for duplicate detection (D-19 B): case, whitespace, end punctuation."""
    return " ".join(text.casefold().split()).rstrip(" .;:!?")


def _dedup_in(group_id: str) -> Callable[[str], Awaitable[bool]]:
    """Duplicate check scoped to the target group: exact normalized fact-text match.

    graphiti-core EntityEdge has no score attribute, so similarity thresholds on
    it are meaningless; D-19 B compares the candidate body with the facts of
    the most relevant edges in the group the candidate would be written to.
    """

    async def _check(body: str) -> bool:
        target = _normalize_fact(body)
        if not target:
            return False
        g = await get_graphiti()
        found = await search_edges(g, body[:256], [group_id], _DEDUP_CANDIDATES)
        return any(_normalize_fact(e.fact) == target for e in found.edges)

    return _check


async def ingest_episode(c: MemoryCandidate) -> dict[str, object]:
    target_group = normalize_group_id((c.group_ids or [SESSION_CURRENT])[0])
    ok, disp = await admission.evaluate(c, _dedup_in(target_group))
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
