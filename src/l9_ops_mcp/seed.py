"""Bootstrap global:decisions from Cursor-Governance CANONICAL_LAW.md.
Safe to re-run: Graphiti deduplicates on ingest.
Usage: python -m l9_ops_mcp.seed [--file /path/to/CANONICAL_LAW.md]
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import re
import sys
from datetime import datetime, timezone

from .graphiti_client import get_graphiti
from .trust_ladder import GLOBAL_DECISIONS


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
    3. ``<repo>/Cursor-Governance`` — the layout scripts/wire_governance_sink.py
       also uses for its sink source.
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


async def seed(path: pathlib.Path | None = None) -> None:
    target = path or _find()
    if target is None or not target.is_file():
        raise SeedInputMissingError([path] if path is not None else _candidates())
    chunks = _chunk(target.read_text(encoding="utf-8"))
    g = await get_graphiti()
    print(f"Seeding {len(chunks)} chunks -> {GLOBAL_DECISIONS} ...")
    for i, chunk in enumerate(chunks):
        await g.add_episode(
            name=f"canonical-law-{i:04d}",
            episode_body=chunk,
            source_description="CANONICAL_LAW.md",
            group_id=GLOBAL_DECISIONS,
            reference_time=datetime.now(timezone.utc),
        )
        if i % 5 == 0:
            print(f"  {i + 1}/{len(chunks)}")
    print(f"Done: {len(chunks)} episodes written to {GLOBAL_DECISIONS}.")


def main() -> None:
    path = None
    if "--file" in sys.argv:
        path = pathlib.Path(sys.argv[sys.argv.index("--file") + 1])
    try:
        asyncio.run(seed(path))
    except SeedInputMissingError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
