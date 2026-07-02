#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from validate_helpers import ROOT, read, rel, status_line, python_syntax_ok

REQUIRED_FRONTMATTER = ("name:", "description:")


def check_skill(skill_dir: Path) -> list[str]:
    out: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    body = read(skill_md)
    if not body.startswith("---"):
        out.append(status_line("FAIL", rel(skill_md), "missing YAML frontmatter"))
    for key in REQUIRED_FRONTMATTER:
        if key not in body.split("---", 2)[1] if body.startswith("---") and body.count("---") >= 2 else True:
            out.append(status_line("FAIL", rel(skill_md), f"missing frontmatter {key}"))
    if "Use when" not in body and "use when" not in body.lower():
        out.append(status_line("WARN", rel(skill_md), "description/body may not contain explicit trigger language"))
    if len(body.splitlines()) > 500:
        out.append(status_line("WARN", rel(skill_md), "SKILL.md exceeds 500 lines; move detail to references/"))
    for script in (skill_dir / "scripts").rglob("*.py") if (skill_dir / "scripts").exists() else []:
        ok, detail = python_syntax_ok(script)
        out.append(status_line("PASS" if ok else "FAIL", rel(script), detail))
    agent_meta = skill_dir / "agents" / "openai.yaml"
    if not agent_meta.exists():
        out.append(status_line("WARN", rel(skill_dir), "agents/openai.yaml missing; installability may depend on target platform"))
    if not out:
        out.append(status_line("PASS", rel(skill_dir), "installability structure ok"))
    return out


def main() -> int:
    skills_root = ROOT / "skills"
    if not skills_root.exists():
        print(status_line("BLOCKED", "skills", "directory missing"))
        return 1
    skill_files = sorted(skills_root.rglob("SKILL.md"))
    if not skill_files:
        print(status_line("BLOCKED", "skills", "no SKILL.md files found"))
        return 1
    failures = 0
    for skill_md in skill_files:
        for line in check_skill(skill_md.parent):
            print(line)
            if line.startswith("FAIL") or line.startswith("BLOCKED"):
                failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
