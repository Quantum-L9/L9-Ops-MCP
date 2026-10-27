"""Bootstrap global:decisions from Cursor-Governance CANONICAL_LAW.md.

Every chunk passes the memory admission gate (D-04 A: single-path rule) with an
explicit high-trust bootstrap provenance; duplicates are merged by the gate.
Exit codes: 0 all chunks admitted or merged; 1 some chunk was rejected or a
write failed (counts are reported); 2 CANONICAL_LAW.md not found.
Usage: python -m l9_ops_mcp.seed [--file /path/to/CANONICAL_LAW.md]
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import re
import sys
from datetime import datetime, timezone

from .memory_ops import ingest_episode
from .models import MemoryCandidate
from .trust_ladder import GLOBAL_DECISIONS

SEED_AGENT_ID = "l9-seed"
SEED_SESSION_ID = "canonical-law-bootstrap"


_LAW = "CANONICAL_LAW.md"


class SeedInputMissingError(FileNotFoundError):
    """CANONICAL_LAW.md was not found at any documented location."""

    def __init__(self, tried: list[pathlib.Path]) -> None:
        self.tried = tried
        listed = "\n".join(f"  - {p}" for p in tried)
        super().__init__(
            f"{_LAW} not found. Locations tried:\n{listed}\n"
            "Set CG_ROOT to a Cursor-Governance checkout or pass --file <path>."
        )


def _candidates() -> list[pathlib.Path]:
    """Documented Cursor-Governance locations, in precedence order.

    1. ``$CG_ROOT`` (only when set and non-empty);
    2. ``~/.cursor-governance`` (the governance SSOT clone);
    3. ``<repo>/Cursor-Governance`` — a sibling checkout inside this repository.
    """
    out: list[pathlib.Path] = []
    cg_root = os.getenv("CG_ROOT")
    if cg_root:
        out.append(pathlib.Path(cg_root) / _LAW)
    out.append(pathlib.Path.home() / ".cursor-governance" / _LAW)
    out.append(pathlib.Path(__file__).resolve().parents[2] / "Cursor-Governance" / _LAW)
    return out


def _find() -> pathlib.Path | None:
    return next((p for p in _candidates() if p.is_file()), None)


def _chunk(text: str, max_chars: int = 800) -> list[str]:
    sections = re.split(r"(?m)^#{1,2} ", text)
    return [s.strip()[:max_chars] for s in sections if len(s.strip()) > 40]


class SeedIncompleteError(RuntimeError):
    """Not every chunk was admitted or merged."""

    def __init__(self, summary: dict[str, object]) -> None:
        self.summary = summary
        rejected = summary["rejected"]
        super().__init__(
            f"seeded {summary['written']} of {summary['total']} chunks into {GLOBAL_DECISIONS}; "
            f"not written: {rejected}"
        )


def _candidate(chunk: str, index: int, source: pathlib.Path) -> MemoryCandidate:
    """Explicit high-trust bootstrap provenance for one CANONICAL_LAW chunk."""
    return MemoryCandidate(
        body=chunk,
        source_agent_id=SEED_AGENT_ID,
        session_id=SEED_SESSION_ID,
        origin_timestamp=datetime.now(timezone.utc),
        group_ids=[GLOBAL_DECISIONS],
        semantic_score=1.0,
        trust_level="L5",
        metadata={"source": str(source), "chunk": index},
    )


def _resolve_target(path: pathlib.Path | None) -> pathlib.Path:
    target = path or _find()
    if target is None or not target.is_file():
        raise SeedInputMissingError([path] if path is not None else _candidates())
    return target


async def _ingest_chunk(
    chunk: str, index: int, source: pathlib.Path, written: int, total: int
) -> str:
    """Admit one chunk; report progress on stderr before re-raising a write failure."""
    try:
        result = await ingest_episode(_candidate(chunk, index, source))
    except Exception:
        print(
            f"seed failed at chunk {index}: {written} of {total} chunks written",
            file=sys.stderr,
        )
        raise
    return str(result["disposition"])


async def seed(path: pathlib.Path | None = None) -> dict[str, object]:
    target = _resolve_target(path)
    chunks = _chunk(target.read_text(encoding="utf-8"))
    print(f"Seeding {len(chunks)} chunks -> {GLOBAL_DECISIONS} through the admission gate ...")
    admitted = merged = 0
    rejected: list[tuple[int, str]] = []
    for i, chunk in enumerate(chunks):
        disposition = await _ingest_chunk(chunk, i, target, admitted + merged, len(chunks))
        if disposition == "admit":
            admitted += 1
        elif disposition == "merge:dedup":
            merged += 1
        else:
            rejected.append((i, disposition))
        if i % 5 == 0:
            print(f"  {i + 1}/{len(chunks)}")
    summary: dict[str, object] = {
        "total": len(chunks),
        "admitted": admitted,
        "merged": merged,
        "written": admitted + merged,
        "rejected": rejected,
    }
    if rejected:
        raise SeedIncompleteError(summary)
    print(f"Done: {admitted} admitted, {merged} merged into {GLOBAL_DECISIONS}.")
    return summary


def main() -> None:
    path = None
    if "--file" in sys.argv:
        path = pathlib.Path(sys.argv[sys.argv.index("--file") + 1])
    try:
        asyncio.run(seed(path))
    except SeedInputMissingError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    except SeedIncompleteError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
