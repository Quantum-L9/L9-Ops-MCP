"""Memory Admission Gateway — memory_admission_kernel.v1, fail_closed."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import MemoryCandidate

LOG = Path("logs/memory-admission-log.jsonl")
QUARANTINE = Path("memory_quarantine")
THRESHOLD = 0.65
MIN_TRUST = "L2"
_ORDER = ["L0", "L1", "L2", "L3", "L4", "L5"]


def _log(d: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as fh:
        fh.write(json.dumps(d) + "\n")


def _ge(a: str, b: str) -> bool:
    return _ORDER.index(a) >= _ORDER.index(b)


async def evaluate(candidate: MemoryCandidate, dedup_check) -> tuple[bool, str]:
    ts = datetime.now(timezone.utc).isoformat()
    base = {
        "session": candidate.session_id,
        "agent": candidate.source_agent_id,
        "ts": ts,
    }

    if candidate.semantic_score < THRESHOLD:
        QUARANTINE.mkdir(parents=True, exist_ok=True)
        qf = QUARANTINE / f"{candidate.session_id}-{int(candidate.origin_timestamp.timestamp())}.json"
        qf.write_text(candidate.model_dump_json(indent=2))
        _log({**base, "criterion": "relevance", "disposition": "quarantine",
              "score": candidate.semantic_score})
        return False, "quarantine:relevance"

    if not _ge(candidate.trust_level, MIN_TRUST):
        _log({**base, "criterion": "trust", "disposition": "block_with_escalation"})
        return False, "block:trust"

    if await dedup_check(candidate.body):
        _log({**base, "criterion": "deduplication", "disposition": "merge"})
        return False, "merge:dedup"

    if not all([candidate.source_agent_id, candidate.session_id, candidate.origin_timestamp]):
        _log({**base, "criterion": "provenance", "disposition": "block"})
        return False, "block:provenance"

    _log({**base, "criterion": "all", "disposition": "admit",
          "score": candidate.semantic_score})
    return True, "admit"
