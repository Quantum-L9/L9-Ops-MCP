#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from validate_helpers import ROOT, read, extract_make_targets, extract_readme_make_commands, status_line


def workflow_commands() -> set[str]:
    cmds: set[str] = set()
    for wf in (ROOT / ".github" / "workflows").glob("*.yml") if (ROOT / ".github" / "workflows").exists() else []:
        text = read(wf)
        cmds.update(re.findall(r"\bmake\s+([A-Za-z0-9_.-]+)", text))
    return cmds


def main() -> int:
    makefile = read(ROOT / "Makefile")
    readme = read(ROOT / "README.md")
    agents = read(ROOT / "AGENTS.md")
    targets = extract_make_targets(makefile)
    referenced = extract_readme_make_commands(readme) | extract_readme_make_commands(agents) | workflow_commands()
    failures = 0
    for cmd in sorted(referenced):
        if cmd not in targets:
            print(status_line("FAIL", "command-parity", f"make {cmd} referenced but missing from Makefile")); failures += 1
        else:
            print(status_line("PASS", "command-parity", f"make {cmd} exists"))
    if not referenced:
        print(status_line("WARN", "command-parity", "no make commands referenced in README/AGENTS/workflows"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
