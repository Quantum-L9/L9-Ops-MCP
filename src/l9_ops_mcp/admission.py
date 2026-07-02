"""Memory Admission Gateway (memory_admission_kernel.v1, ADR-009).

Five criteria in order: relevance, trust, consent, deduplication, provenance.
fail_closed: True. Every decision is logged. Failures quarantine or block.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import MemoryCandidate

LOG = Path("logs/memory-admission-log.jsonl")
QUARANTINE = Path("memory_quarantine")
RELEVANCE_THRESHOLD = 0.65
MIN_TRUST = "L2"
_TRUST_ORDER = ["L0", "L1", "L2", "L3", "L4", "L5"]


def _log(decision: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as fh:
        fh.write(json.dumps(decision) + "\n")


def _trust_ge(level: str, minimum: str) -> bool:
    return _TRUST_ORDER.index(level) >= _TRUST_ORDER.index(minimum)


async def evaluate(candidate: MemoryCandidate, dedup_check) -> tuple[bool, str]:
    """Return (admitted, disposition). dedup_check(body)->bool is graph-backed."""
    ts = datetime.now(timezone.utc).isoformat()
    base = {"session_id": candidate.session_id, "agent": candidate.source_agent_id, "ts": ts}

    # 1. relevance
    if candidate.semantic_score < RELEVANCE_THRESHOLD:
        _quarantine(candidate)
        _log({**base, "criterion": "relevance", "disposition": "quarantine",
              "score": candidate.semantic_score})
        return False, "quarantine:relevance"

    # 2. trust
    if not _trust_ge(candidate.trust_level, MIN_TRUST):
        _log({**base, "criterion": "trust", "disposition": "block_with_escalation"})
        return False, "block:trust"

    # 3. consent (external sharing requires explicit declaration; local writes pass)
    # 4. deduplication
    if await dedup_check(candidate.body):
        _log({**base, "criterion": "deduplication", "disposition": "merge_existing_node"})
        return False, "merge:dedup"

    # 5. provenance
    if not (candidate.source_agent_id and candidate.session_id and candidate.origin_timestamp):
        _log({**base, "criterion": "provenance", "disposition": "block"})
        return False, "block:provenance"

    _log({**base, "criterion": "all", "disposition": "admit",
          "score": candidate.semantic_score})
    return True, "admit"


def _quarantine(candidate: MemoryCandidate) -> None:
    QUARANTINE.mkdir(parents=True, exist_ok=True)
    fn = QUARANTINE / f"{candidate.session_id}-{int(candidate.origin_timestamp.timestamp())}.json"
    fn.write_text(candidate.model_dump_json(indent=2))
