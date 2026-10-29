#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from validate_helpers import ROOT, MetadataError, load_metadata, status_line

SCHEMA_KEYS = ("properties", "required")


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def check_handoff_schema(schema: Path) -> str | None:
    """Return a failure reason, or None when the schema is structurally usable."""
    try:
        data = load_metadata(schema)
    except (MetadataError, UnicodeDecodeError) as exc:
        return f"handoff schema does not parse: {exc}"
    if not isinstance(data, dict):
        return "handoff schema is not a mapping"
    if not any(key in data for key in SCHEMA_KEYS):
        return "handoff schema has no top-level properties/required keys"
    return None


def _check_entrypoint(pb: Path, root: Path) -> int:
    """Print the entrypoint verdict (and steps/ warning); return the FAIL count."""
    failures = 0
    entry = pb / "PLAYBOOK.md"
    alt = pb / "playbook.yaml"
    if not entry.exists() and not alt.exists():
        print(status_line("FAIL", _rel(pb, root), "missing PLAYBOOK.md or playbook.yaml"))
        failures += 1
    else:
        print(
            status_line("PASS", _rel(entry if entry.exists() else alt, root), "entrypoint exists")
        )
    if not (pb / "steps").exists() and entry.exists():
        print(status_line("WARN", _rel(pb, root), "markdown playbook has no steps/ directory"))
    return failures


def _check_handoffs(pb: Path, root: Path) -> int:
    """Print a verdict per handoff schema; return the FAIL count."""
    handoffs = pb / "handoffs"
    if not handoffs.is_dir():
        return 0
    failures = 0
    schemas = sorted(
        p for p in handoffs.rglob("*") if p.is_file() and p.suffix in {".yaml", ".yml"}
    )
    for schema in schemas:
        reason = check_handoff_schema(schema)
        if reason:
            print(status_line("FAIL", _rel(schema, root), reason))
            failures += 1
        else:
            print(status_line("PASS", _rel(schema, root), "handoff schema is structural"))
    return failures


def main(root: Path = ROOT) -> int:
    playbooks = root / "playbooks"
    if not playbooks.is_dir():
        print(status_line("BLOCKED", "playbooks", "directory missing"))
        return 1
    failures = 0
    found = 0
    for pb in sorted(p for p in playbooks.iterdir() if p.is_dir()):
        found += 1
        failures += _check_entrypoint(pb, root)
        failures += _check_handoffs(pb, root)
    if found == 0:
        print(status_line("BLOCKED", "playbooks", "no playbook directories found"))
        return 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
