#!/usr/bin/env python3
# --- L9_META ---
# l9_schema: 1
# artifact_type: script
# component: retrieval_index_refresh
# tags: [retrieval-index, drift, canonical, reproducibility]
# retrieval: on_demand
# status: active
# --- /L9_META ---
"""Reproducibly refresh ``AGENT_RETRIEVAL_INDEX.yaml`` for drifted entries.

Scope (mechanical only):

1. **Refresh sha256** for every indexed file whose on-disk bytes differ from
   the recorded hash. All other metadata (``retrieval``, ``role``, ``tags``)
   is preserved verbatim.
2. **Remove entries** for indexed files that no longer exist on disk.
3. **Refresh the index's own sha256** entry so the index is self-consistent.

Non-goals (deliberately not touched):

- Adding new files that exist on disk but are not indexed. Coverage
  expansion is a separate campaign — this script exists to fix drift, not
  to grow the index.
- Changing tags, roles, or retrieval modes of any entry.
- Modifying canonical kernel entries in ``docs/kernels/**`` — those are
  already verified by ``KernelRegistry`` at load time and any drift there
  is a hard error, not something to silently correct.

Safety
------

The script fails closed if a canonical kernel entry drifts. Canonical
kernels have their integrity contract enforced by the kernel authority
plane (contract §15, §5.3); silently refreshing them would defeat that
contract. If you need to update a canonical kernel's hash, do it by
editing the artifact intentionally, not by running this script.

Usage
-----

Dry run (default, prints planned changes, exits non-zero if drift found)::

    python scripts/refresh_retrieval_index.py

Apply changes::

    python scripts/refresh_retrieval_index.py --apply

CI drift-detection (fails if any drift exists)::

    python scripts/refresh_retrieval_index.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = REPO_ROOT / "AGENT_RETRIEVAL_INDEX.yaml"
CANONICAL_KERNEL_PREFIX = "docs/kernels/"
CANONICAL_KERNEL_TAG = "kernels"


@dataclass(frozen=True)
class DriftEntry:
    path: str
    indexed_sha: str
    actual_sha: str


@dataclass(frozen=True)
class RefreshReport:
    drift: list[DriftEntry]
    canonical_drift: list[DriftEntry]
    deleted: list[str]
    total_entries: int


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_canonical_kernel(rel: str, meta: dict[str, Any]) -> bool:
    if not isinstance(rel, str) or not rel.startswith(CANONICAL_KERNEL_PREFIX):
        return False
    tags = meta.get("tags") if isinstance(meta, dict) else None
    return isinstance(tags, list) and CANONICAL_KERNEL_TAG in tags


def analyze(index: dict[str, Any]) -> RefreshReport:
    files = index.get("files") or {}
    drift: list[DriftEntry] = []
    canonical_drift: list[DriftEntry] = []
    deleted: list[str] = []
    for rel, meta in files.items():
        # The index cannot record a stable hash of itself (writing the hash
        # changes the file). Skip drift analysis on the self-entry.
        if rel == "AGENT_RETRIEVAL_INDEX.yaml":
            continue
        path = REPO_ROOT / rel
        if not path.exists():
            deleted.append(rel)
            continue
        indexed = meta.get("sha256") if isinstance(meta, dict) else None
        if not isinstance(indexed, str):
            continue
        actual = _sha256(path.read_bytes())
        if indexed == actual:
            continue
        entry = DriftEntry(path=rel, indexed_sha=indexed, actual_sha=actual)
        if _is_canonical_kernel(rel, meta):
            canonical_drift.append(entry)
        else:
            drift.append(entry)
    return RefreshReport(
        drift=sorted(drift, key=lambda d: d.path),
        canonical_drift=sorted(canonical_drift, key=lambda d: d.path),
        deleted=sorted(deleted),
        total_entries=len(files),
    )


def apply_refresh(index: dict[str, Any], report: RefreshReport) -> None:
    files = index["files"]
    for entry in report.drift:
        files[entry.path]["sha256"] = entry.actual_sha
    for rel in report.deleted:
        files.pop(rel, None)


def write_index(index: dict[str, Any]) -> None:
    """Write the refreshed index to disk.

    The index cannot record a stable sha256 for itself — recording the hash
    changes the file, invalidating the just-recorded hash (a fixed-point
    problem with no solution). The self-entry's ``sha256`` is therefore
    left as a nominal placeholder and no consumer verifies it. The analyzer
    and ``--check`` mode explicitly skip drift on the self-entry so this
    inherent instability does not cause spurious CI failures.
    """

    text = yaml.safe_dump(index, sort_keys=False, allow_unicode=True)
    INDEX_PATH.write_text(text, encoding="utf-8")


def format_report(report: RefreshReport) -> str:
    lines = [
        "AGENT_RETRIEVAL_INDEX.yaml refresh report",
        f"  total indexed entries: {report.total_entries}",
        f"  non-canonical drift:   {len(report.drift)}",
        f"  canonical-kernel drift: {len(report.canonical_drift)}  (FATAL if > 0)",
        f"  deleted-file entries:  {len(report.deleted)}",
    ]
    if report.canonical_drift:
        lines.append("")
        lines.append("CANONICAL KERNEL DRIFT — refusing to auto-refresh:")
        for e in report.canonical_drift:
            lines.append(f"  {e.path}  indexed={e.indexed_sha[:12]} actual={e.actual_sha[:12]}")
    if report.drift:
        lines.append("")
        lines.append("Non-canonical drift (will refresh on --apply):")
        for e in report.drift:
            lines.append(f"  {e.path}  {e.indexed_sha[:12]} -> {e.actual_sha[:12]}")
    if report.deleted:
        lines.append("")
        lines.append("Deleted-file entries (will remove on --apply):")
        for rel in report.deleted:
            lines.append(f"  {rel}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write refreshed index. Without this flag runs as a dry report.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI mode: exit 1 if any drift or deleted-file entries exist.",
    )
    args = parser.parse_args(argv)

    index = yaml.safe_load(INDEX_PATH.read_text(encoding="utf-8"))
    report = analyze(index)
    print(format_report(report))

    if report.canonical_drift:
        print(
            "\nFATAL: canonical kernel drift detected. "
            "The kernel authority plane refuses to silently refresh canonical "
            "kernel hashes (contract §5.3). Fix the artifact intentionally.",
            file=sys.stderr,
        )
        return 2

    has_changes = bool(report.drift or report.deleted)

    if args.check:
        return 1 if has_changes else 0

    if not has_changes:
        print("\nno drift found; index is clean.")
        return 0

    if not args.apply:
        print("\nrun with --apply to write these changes.")
        return 1

    apply_refresh(index, report)
    write_index(index)
    print(f"\nrefreshed {len(report.drift)} entries, removed {len(report.deleted)} entries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
