"""Single durable write path, gated by the admission gate."""

from __future__ import annotations

import json

from . import admission
from .graphiti_client import get_graphiti, search_edges
from .models import MemoryCandidate
from .trust_ladder import (
    SESSION_CURRENT,
    allowed_scopes,
    normalize_group_id,
    validate_trust_level,
)


_DEDUP_CANDIDATES = 10


def _normalize_fact(text: str) -> str:
    """Normalization for duplicate detection (D-19 B): case, whitespace, end punctuation."""
    return " ".join(text.casefold().split()).rstrip(" .;:!?")


class _GroupDedup:
    """Duplicate check scoped to the target group: exact normalized fact-text match.

    graphiti-core EntityEdge has no score attribute, so similarity thresholds on
    it are meaningless; D-19 B compares the candidate body with the facts of
    the most relevant edges in the group the candidate would be written to.
    The matched edge uuid is kept for the merge (D-03 A).
    """

    def __init__(self, group_id: str) -> None:
        self.group_id = group_id
        self.matched_uuid: str | None = None

    async def __call__(self, body: str) -> bool:
        target = _normalize_fact(body)
        if not target:
            return False
        g = await get_graphiti()
        found = await search_edges(g, body[:256], [self.group_id], _DEDUP_CANDIDATES)
        for e in found.edges:
            if _normalize_fact(e.fact) == target:
                self.matched_uuid = str(e.uuid)
                return True
        return False


# Merge (D-03 A): no new episode; the candidate's provenance is appended to the
# existing fact edge. l9_provenance is a list of JSON strings (Neo4j property
# lists must be homogeneous primitives); graphiti-core reads unknown edge
# properties into EntityEdge.attributes and writes them back on save, so the
# list survives graphiti's own edge updates.
_MERGE_PROVENANCE_CYPHER = """
MATCH (:Entity)-[e:RELATES_TO {uuid: $uuid}]->(:Entity)
SET e.l9_provenance = coalesce(e.l9_provenance, []) + [$provenance]
RETURN e.uuid AS uuid
"""


def _provenance(c: MemoryCandidate) -> dict[str, str]:
    return {
        "agent": c.source_agent_id,
        "session": c.session_id,
        "ts": c.origin_timestamp.isoformat(),
    }


async def _merge(c: MemoryCandidate, edge_uuid: str | None) -> dict[str, object]:
    """Append provenance to the duplicate fact; on any failure quarantine the candidate."""
    prov = _provenance(c)
    try:
        if edge_uuid is None:
            msg = "duplicate reported without a matched fact edge"
            raise LookupError(msg)
        g = await get_graphiti()
        records, _, _ = await g.driver.execute_query(
            _MERGE_PROVENANCE_CYPHER,
            uuid=edge_uuid,
            provenance=json.dumps(prov, sort_keys=True),
        )
        if not records:
            msg = f"fact edge {edge_uuid} not found for merge"
            raise LookupError(msg)
    except Exception as exc:  # merge failure must not lose the candidate
        admission.quarantine(
            c,
            "deduplication",
            reason=f"merge failed: {type(exc).__name__}: {exc}",
            edge=edge_uuid,
        )
        return {"admitted": False, "disposition": "quarantine:merge"}
    admission.log_decision(c, "deduplication", "merged", edge=edge_uuid)
    return {
        "admitted": False,
        "disposition": "merge:dedup",
        "merged_into": edge_uuid,
        "provenance": prov,
    }


def _writable(agent_id: str, trust_level: str, group: str) -> bool:
    """A writer may only target, and so only dedup-search, a group it may read."""
    scopes = allowed_scopes(agent_id, validate_trust_level(trust_level))
    return scopes == ["*"] or group in scopes


async def ingest_episode(c: MemoryCandidate) -> dict[str, object]:
    target_group = normalize_group_id((c.group_ids or [SESSION_CURRENT])[0])
    if not _writable(c.source_agent_id, c.trust_level, target_group):
        # Decided before admission.evaluate so no search touches a group the
        # writer cannot read and no edge uuid from it is ever disclosed.
        admission.log_decision(c, "scope", "block", group=target_group)
        return {"admitted": False, "disposition": "block:scope"}
    dedup = _GroupDedup(target_group)
    ok, disp = await admission.evaluate(c, dedup)
    if disp == "merge:dedup":
        return await _merge(c, dedup.matched_uuid)
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
        "provenance": _provenance(c),
    }
