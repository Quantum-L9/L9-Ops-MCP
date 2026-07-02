#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from validate_helpers import ROOT, rel, read, status_line


def main() -> int:
    root = ROOT / "playbooks"
    if not root.exists():
        print(status_line("BLOCKED", "playbooks", "directory missing"))
        return 1
    failures = 0
    found = 0
    for pb in sorted(p for p in root.iterdir() if p.is_dir()):
        found += 1
        entry = pb / "PLAYBOOK.md"
        alt = pb / "playbook.yaml"
        if not entry.exists() and not alt.exists():
            print(status_line("FAIL", rel(pb), "missing PLAYBOOK.md or playbook.yaml")); failures += 1
        else:
            print(status_line("PASS", rel(entry if entry.exists() else alt), "entrypoint exists"))
        if not (pb / "steps").exists() and entry.exists():
            print(status_line("WARN", rel(pb), "markdown playbook has no steps/ directory"))
        if (pb / "handoffs").exists():
            for schema in (pb / "handoffs").rglob("*.yaml"):
                text = read(schema)
                if "required" not in text and "properties" not in text:
                    print(status_line("WARN", rel(schema), "schema-like handoff lacks required/properties markers"))
                else:
                    print(status_line("PASS", rel(schema), "handoff schema has structural markers"))
    if found == 0:
        print(status_line("BLOCKED", "playbooks", "no playbook directories found")); return 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
