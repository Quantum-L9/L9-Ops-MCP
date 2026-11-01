#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from validate_helpers import (
    ROOT,
    read,
    extract_make_targets,
    extract_readme_make_commands,
    status_line,
)

WORKFLOW_SUFFIXES = (".yml", ".yaml")


def workflow_commands(root: Path = ROOT) -> set[str]:
    cmds: set[str] = set()
    workflows = root / ".github" / "workflows"
    if not workflows.is_dir():
        return cmds
    for wf in sorted(workflows.iterdir()):
        if wf.is_file() and wf.suffix in WORKFLOW_SUFFIXES:
            cmds.update(extract_readme_make_commands(read(wf)))
    return cmds


def main(root: Path = ROOT) -> int:
    failures = 0
    for required in ("Makefile", "README.md"):
        if not (root / required).is_file():
            print(status_line("FAIL", "command-parity", f"{required} missing"))
            failures += 1
    if failures:
        return 1
    targets = extract_make_targets(read(root / "Makefile"))
    referenced = (
        extract_readme_make_commands(read(root / "README.md"))
        | extract_readme_make_commands(read(root / "AGENTS.md"))
        | workflow_commands(root)
    )
    for cmd in sorted(referenced):
        if cmd not in targets:
            print(
                status_line(
                    "FAIL", "command-parity", f"make {cmd} referenced but missing from Makefile"
                )
            )
            failures += 1
        else:
            print(status_line("PASS", "command-parity", f"make {cmd} exists"))
    if not referenced:
        print(
            status_line(
                "WARN", "command-parity", "no make commands referenced in README/AGENTS/workflows"
            )
        )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
