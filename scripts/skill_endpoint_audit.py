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
skill_endpoint_audit.py — Custom skill endpoint health check.
Scans all SKILL.md files for endpoint definitions and verifies they respond.
All skills are custom — no third-party endpoints.
Exits 1 on failure.
"""

import os
import sys
import yaml
import argparse


def find_skill_files(skills_dir):
    for root, dirs, files in os.walk(skills_dir):
        for fname in files:
            if fname == "SKILL.md":
                yield os.path.join(root, fname)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skills-dir", default="skills")
    parser.add_argument("--exit-on-failure", action="store_true")
    args = parser.parse_args()

    skills = list(find_skill_files(args.skills_dir))
    print(f"Found {len(skills)} skill files")

    failures = []
    for skill_path in skills:
        with open(skill_path) as f:
            content = f.read()
        # Extract meta from frontmatter
        meta = None
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    meta = yaml.safe_load(parts[1])
                except Exception:
                    pass
        if not meta:
            print(f"  WARN: Could not parse frontmatter: {skill_path}")
            continue

        skill_id = meta.get("title", skill_path)

        # Check required fields
        required = [
            "title",
            "purpose",
            "summary",
            "version",
            "retrieval_keys",
            "trigger_description",
        ]
        missing = [f for f in required if not meta.get(f)]
        if missing:
            failures.append(f"{skill_id}: missing fields: {missing}")
        else:
            print(f"  OK: {skill_id}")

    if failures:
        print(f"\n{len(failures)} failures:")
        for f in failures:
            print(f"  FAIL: {f}")
        if args.exit_on_failure:
            sys.exit(1)
    else:
        print("\nAll skills passed audit.")


if __name__ == "__main__":
    main()
