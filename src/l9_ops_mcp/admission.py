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
TRUST_ORDER: tuple[str, ...] = ("L0", "L1", "L2", "L3", "L4", "L5")


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


def trust_at_least(level: str, minimum: str) -> bool:
    return TRUST_ORDER.index(level) >= TRUST_ORDER.index(minimum)


async def evaluate(
    candidate: MemoryCandidate,
    dedup_check: Callable[[str], Awaitable[bool]],
) -> tuple[bool, str]:
    base = decision_base(candidate)

    if candidate.semantic_score < THRESHOLD:
        quarantine(candidate, "relevance", base, score=candidate.semantic_score)
        return False, "quarantine:relevance"

    if not trust_at_least(candidate.trust_level, MIN_TRUST):
        _log({**base, "criterion": "trust", "disposition": "block_with_escalation"})
        return False, "block:trust"

    if candidate.external_sharing and candidate.consent != "granted":
        _log({**base, "criterion": "consent", "disposition": "block"})
        return False, "block:consent"

    provenance_ok = all(
        [candidate.source_agent_id, candidate.session_id, candidate.origin_timestamp]
    )

    if await dedup_check(candidate.body):
        # A merge writes the candidate's provenance onto the existing fact, so
        # it needs the same provenance stamp an admitted write does.
        if not provenance_ok:
            _log({**base, "criterion": "provenance", "disposition": "block"})
            return False, "block:provenance"
        _log({**base, "criterion": "deduplication", "disposition": "merge"})
        return False, "merge:dedup"

    if not provenance_ok:
        _log({**base, "criterion": "provenance", "disposition": "block"})
        return False, "block:provenance"

    _log({**base, "criterion": "all", "disposition": "admit", "score": candidate.semantic_score})
    return True, "admit"


def decision_base(candidate: MemoryCandidate) -> dict[str, object]:
    return {
        "session": candidate.session_id,
        "agent": candidate.source_agent_id,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def log_event(record: dict[str, object]) -> None:
    """Append a memory-write decision that has no candidate (e.g. a fact invalidation)."""
    _log({"ts": datetime.now(timezone.utc).isoformat(), **record})


def log_decision(
    candidate: MemoryCandidate, criterion: str, disposition: str, **extra: object
) -> None:
    """Record a post-gate decision (e.g. a completed merge) in the admission log."""
    _log({**decision_base(candidate), "criterion": criterion, "disposition": disposition, **extra})


def quarantine(
    candidate: MemoryCandidate,
    criterion: str,
    base: dict[str, object] | None = None,
    **extra: object,
) -> Path:
    """Retain a candidate in memory_quarantine/ with a logged rationale.

    The decision is logged before the write so a write failure cannot drop it;
    a write failure is logged with the error and the full candidate, then
    raised as :class:`QuarantineWriteError`.
    """
    base = base if base is not None else decision_base(candidate)
    qf = _quarantine_path(candidate)
    _log(
        {
            **base,
            "criterion": criterion,
            "disposition": "quarantine",
            **extra,
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
                "criterion": criterion,
                "disposition": "quarantine_write_failed",
                "error": f"{type(exc).__name__}: {exc}",
                "candidate": candidate.model_dump(mode="json"),
            }
        )
        msg = f"quarantine write failed for session {candidate.session_id!r}: {exc}"
        raise QuarantineWriteError(msg) from exc
    return qf
