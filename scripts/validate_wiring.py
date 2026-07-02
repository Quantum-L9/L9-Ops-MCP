#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from validate_helpers import ROOT, read, rel, status_line, find_markdown_links, python_syntax_ok


def check_agents_links() -> int:
    failures = 0
    text = read(ROOT / "AGENTS.md")
    for link in find_markdown_links(text):
        if link.startswith("http") or link.startswith("#"):
            continue
        target = (ROOT / link).resolve()
        if not str(target).startswith(str(ROOT)):
            print(status_line("FAIL", "AGENTS.md", f"unsafe link escapes repo: {link}")); failures += 1
        elif not target.exists():
            print(status_line("FAIL", "AGENTS.md", f"broken registry link: {link}")); failures += 1
        else:
            print(status_line("PASS", "AGENTS.md", f"registry link exists: {link}"))
    return failures


def check_workflow_scripts() -> int:
    failures = 0
    for wf in (ROOT / ".github" / "workflows").glob("*.yml") if (ROOT / ".github" / "workflows").exists() else []:
        text = read(wf)
        for script in re.findall(r"(?:bash|python3?)\s+(scripts/[A-Za-z0-9_./-]+)", text):
            path = ROOT / script
            if not path.exists():
                print(status_line("FAIL", rel(wf), f"referenced script missing: {script}")); failures += 1
            else:
                print(status_line("PASS", rel(wf), f"referenced script exists: {script}"))
    return failures


def check_python_syntax() -> int:
    failures = 0
    for path in sorted((ROOT / "scripts").glob("*.py")) if (ROOT / "scripts").exists() else []:
        ok, detail = python_syntax_ok(path)
        print(status_line("PASS" if ok else "FAIL", rel(path), detail))
        failures += 0 if ok else 1
    return failures


def run_validator(path: str) -> int:
    full = ROOT / path
    if not full.exists():
        print(status_line("FAIL", path, "validator missing")); return 1
    proc = subprocess.run([sys.executable, str(full)], cwd=str(ROOT), text=True, capture_output=True)
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip())
    print(status_line("PASS" if proc.returncode == 0 else "FAIL", path, f"exit={proc.returncode}"))
    return 0 if proc.returncode == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    failures = 0
    failures += check_agents_links()
    failures += check_workflow_scripts()
    failures += check_python_syntax()
    for validator in [
        "scripts/validate_command_parity.py",
        "scripts/validate_pyproject_entrypoints.py",
        "scripts/validate_skill_installability.py",
        "scripts/validate_playbooks.py",
        "scripts/validate_org_invariants.py",
        "scripts/validate_upload_router.py",
    ]:
        failures += run_validator(validator)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
