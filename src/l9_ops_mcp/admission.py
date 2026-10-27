"""Memory Admission Gateway — memory_admission_kernel.v1, fail_closed."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .models import MemoryCandidate

LOG = Path("logs/memory-admission-log.jsonl")
QUARANTINE = Path("memory_quarantine")
THRESHOLD = 0.65
MIN_TRUST = "L2"
_ORDER = ["L0", "L1", "L2", "L3", "L4", "L5"]


def _log(d: dict[str, object]) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as fh:
        fh.write(json.dumps(d) + "\n")


class QuarantineWriteError(OSError):
    """A quarantined candidate could not be written; the decision and candidate are logged."""


def _quarantine_path(candidate: MemoryCandidate) -> Path:
    """Unique, confined quarantine file for one candidate.

    The session id is untrusted input, so it is hashed rather than used as a
    path component; a per-candidate uuid keeps same-second candidates apart.
    """
    session_key = hashlib.sha256(candidate.session_id.encode("utf-8")).hexdigest()[:16]
    ts = int(candidate.origin_timestamp.timestamp())
    qf = QUARANTINE / f"{session_key}-{ts}-{uuid.uuid4().hex}.json"
    root = QUARANTINE.resolve()
    if qf.resolve().parent != root:  # defence in depth; the name has no separators
        msg = f"quarantine path escapes {root}: {qf}"
        raise QuarantineWriteError(msg)
    return qf


def _ge(a: str, b: str) -> bool:
    return _ORDER.index(a) >= _ORDER.index(b)


async def evaluate(
    candidate: MemoryCandidate,
    dedup_check: Callable[[str], Awaitable[bool]],
) -> tuple[bool, str]:
    ts = datetime.now(timezone.utc).isoformat()
    base = {
        "session": candidate.session_id,
        "agent": candidate.source_agent_id,
        "ts": ts,
    }

    if candidate.semantic_score < THRESHOLD:
        qf = _quarantine_path(candidate)
        # Log the decision before the write so a write failure cannot drop it.
        _log(
            {
                **base,
                "criterion": "relevance",
                "disposition": "quarantine",
                "score": candidate.semantic_score,
                "quarantine_file": qf.name,
            }
        )
        try:
            QUARANTINE.mkdir(parents=True, exist_ok=True)
            qf.write_text(candidate.model_dump_json(indent=2))
        except OSError as exc:
            _log(
                {
                    **base,
                    "criterion": "relevance",
                    "disposition": "quarantine_write_failed",
                    "error": f"{type(exc).__name__}: {exc}",
                    "candidate": candidate.model_dump(mode="json"),
                }
            )
            msg = f"quarantine write failed for session {candidate.session_id!r}: {exc}"
            raise QuarantineWriteError(msg) from exc
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

    _log({**base, "criterion": "all", "disposition": "admit", "score": candidate.semantic_score})
    return True, "admit"
