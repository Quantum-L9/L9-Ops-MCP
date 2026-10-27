#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from validate_helpers import (
    ROOT,
    MetadataError,
    parse_frontmatter,
    read,
    rel,
    status_line,
    python_syntax_ok,
)

REQUIRED_FRONTMATTER = ("name", "description")


def _frontmatter_fields(skill_md: Path, body: str, out: list[str]) -> dict[str, Any]:
    """Parse the frontmatter, appending a FAIL line to ``out`` when it is unusable."""
    try:
        meta = parse_frontmatter(body) if body.startswith("---") else None
    except MetadataError as exc:
        out.append(status_line("FAIL", rel(skill_md), f"invalid YAML frontmatter: {exc}"))
        return {}
    if meta is None:
        out.append(status_line("FAIL", rel(skill_md), "missing YAML frontmatter"))
    elif not isinstance(meta, dict):
        out.append(status_line("FAIL", rel(skill_md), "frontmatter is not a mapping"))
    return meta if isinstance(meta, dict) else {}


def _frontmatter_lines(skill_md: Path, body: str) -> list[str]:
    out: list[str] = []
    fields = _frontmatter_fields(skill_md, body, out)
    for key in REQUIRED_FRONTMATTER:
        value = fields.get(key)
        if not isinstance(value, str) or not value.strip():
            out.append(status_line("FAIL", rel(skill_md), f"missing frontmatter {key}:"))
    return out


def _body_lines(skill_md: Path, body: str) -> list[str]:
    out: list[str] = []
    if "Use when" not in body and "use when" not in body.lower():
        out.append(
            status_line(
                "WARN", rel(skill_md), "description/body may not contain explicit trigger language"
            )
        )
    if len(body.splitlines()) > 500:
        out.append(
            status_line(
                "WARN", rel(skill_md), "SKILL.md exceeds 500 lines; move detail to references/"
            )
        )
    return out


def _script_lines(skill_dir: Path) -> list[str]:
    out: list[str] = []
    for script in (skill_dir / "scripts").rglob("*.py") if (skill_dir / "scripts").exists() else []:
        ok, detail = python_syntax_ok(script)
        out.append(status_line("PASS" if ok else "FAIL", rel(script), detail))
    return out


def _agent_meta_lines(skill_dir: Path) -> list[str]:
    agent_meta = skill_dir / "agents" / "openai.yaml"
    if agent_meta.exists():
        return []
    return [
        status_line(
            "WARN",
            rel(skill_dir),
            "agents/openai.yaml missing; installability may depend on target platform",
        )
    ]


def check_skill(skill_dir: Path) -> list[str]:
    skill_md = skill_dir / "SKILL.md"
    body = read(skill_md)
    out = _frontmatter_lines(skill_md, body)
    out += _body_lines(skill_md, body)
    out += _script_lines(skill_dir)
    out += _agent_meta_lines(skill_dir)
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
