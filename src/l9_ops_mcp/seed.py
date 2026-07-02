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


def _find() -> pathlib.Path | None:
    candidates = [
        pathlib.Path(os.getenv("CG_ROOT", "")) / "CANONICAL_LAW.md",
        pathlib.Path.home() / ".cursor-governance" / "CANONICAL_LAW.md",
        pathlib.Path(__file__).parents[4] / "Cursor-Governance" / "CANONICAL_LAW.md",
    ]
    return next((p for p in candidates if p.exists()), None)


def _chunk(text: str, max_chars: int = 800) -> list[str]:
    sections = re.split(r"(?m)^#{1,2} ", text)
    return [s.strip()[:max_chars] for s in sections if len(s.strip()) > 40]


async def seed(path: pathlib.Path | None = None) -> None:
    target = path or _find()
    if target is None or not target.exists():
        print("CANONICAL_LAW.md not found. Set CG_ROOT or use --file.")
        return
    chunks = _chunk(target.read_text(encoding="utf-8"))
    g = await get_graphiti()
    print(f"Seeding {len(chunks)} chunks -> global:decisions ...")
    for i, chunk in enumerate(chunks):
        await g.add_episode(
            name=f"canonical-law-{i:04d}",
            episode_body=chunk,
            source_description="CANONICAL_LAW.md",
            group_id="global:decisions",
            reference_time=datetime.now(timezone.utc),
        )
        if i % 5 == 0:
            print(f"  {i+1}/{len(chunks)}")
    print(f"Done: {len(chunks)} episodes written to global:decisions.")


def main() -> None:
    path = None
    if "--file" in sys.argv:
        path = pathlib.Path(sys.argv[sys.argv.index("--file") + 1])
    asyncio.run(seed(path))


if __name__ == "__main__":
    main()
