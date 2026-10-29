# --- L9_META ---
# l9_schema: 1
# component: skill_endpoint_audit
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

#!/usr/bin/env python3
"""
skill_endpoint_audit.py — Custom skill metadata audit.
Scans every SKILL.md under --skills-dir (default: the repository's skills/)
and checks that its YAML frontmatter is a mapping carrying the required
retrieval fields. No network calls are made.
Exits 1 when any skill fails, when the directory is missing, or when it
contains no SKILL.md files. --exit-on-failure is accepted for compatibility;
failures always exit 1.
"""

import argparse
import sys
from pathlib import Path

from validate_helpers import MetadataError, missing_fields, parse_frontmatter, resolve_repo_path

REQUIRED = (
    "title",
    "purpose",
    "summary",
    "version",
    "retrieval_keys",
    "trigger_description",
)


def find_skill_files(skills_dir: Path) -> list[Path]:
    return sorted(p for p in skills_dir.rglob("SKILL.md") if p.is_file())


def audit_skill(skill_path: Path) -> str | None:
    """Return a failure description, or None when the skill passes."""
    try:
        meta = parse_frontmatter(skill_path.read_text(encoding="utf-8"))
    except (MetadataError, UnicodeDecodeError) as exc:
        return f"{skill_path}: unparseable frontmatter: {exc}"
    if meta is None:
        return f"{skill_path}: no YAML frontmatter"
    if not isinstance(meta, dict):
        return f"{skill_path}: frontmatter is not a mapping"
    missing = missing_fields(meta, REQUIRED)
    if missing:
        return f"{meta.get('title') or skill_path}: missing fields: {missing}"
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skills-dir", default="skills")
    parser.add_argument(
        "--exit-on-failure",
        action="store_true",
        help="accepted for compatibility; failures always exit 1",
    )
    args = parser.parse_args()

    skills_dir = resolve_repo_path(args.skills_dir)
    if not skills_dir.is_dir():
        print(f"  FAIL: skills directory not found: {skills_dir}")
        return 1
    skills = find_skill_files(skills_dir)
    print(f"Found {len(skills)} skill files")
    if not skills:
        print(f"  FAIL: no SKILL.md files under {skills_dir}")
        return 1

    failures = []
    for skill_path in skills:
        failure = audit_skill(skill_path)
        if failure:
            failures.append(failure)
        else:
            print(f"  OK: {skill_path}")

    if failures:
        print(f"\n{len(failures)} failures:")
        for failure in failures:
            print(f"  FAIL: {failure}")
        return 1
    print("\nAll skills passed audit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
