# --- L9_META ---
# l9_schema: 1
# component: validate_headers
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

#!/usr/bin/env python3
"""
validate_headers.py — Enforce canonical headers on all kernels and skills.
Usage: python3 scripts/validate_headers.py --dir docs/kernels --ext .yaml --required title,purpose,summary,...
Exits 1 if any file is missing required fields.
"""

import sys
import os
import argparse
import yaml


def check_yaml_frontmatter(filepath, required_fields):
    with open(filepath) as f:
        content = f.read()
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1])
                if meta is None:
                    return [f"Empty frontmatter in {filepath}"]
                missing = [field for field in required_fields if field not in meta]
                return [f"{filepath}: missing field '{f}'" for f in missing]
            except yaml.YAMLError as e:
                return [f"{filepath}: YAML parse error: {e}"]
    # Try full YAML parse (for .yaml files without --- wrapper)
    try:
        with open(filepath) as f:
            meta = yaml.safe_load(f)
        if not isinstance(meta, dict):
            return [f"{filepath}: not a dict"]
        missing = [field for field in required_fields if field not in meta]
        return [f"{filepath}: missing field '{f}'" for f in missing]
    except Exception as e:
        return [f"{filepath}: parse error: {e}"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    parser.add_argument("--ext", default=".yaml")
    parser.add_argument("--required", required=True)
    args = parser.parse_args()

    required_fields = [f.strip() for f in args.required.split(",")]
    errors = []

    for root, dirs, files in os.walk(args.dir):
        for fname in files:
            if fname.endswith(args.ext):
                path = os.path.join(root, fname)
                errors.extend(check_yaml_frontmatter(path, required_fields))

    if errors:
        for e in errors:
            print(f"  FAIL: {e}")
        sys.exit(1)
    else:
        print(f"  OK: All files in {args.dir} have required headers.")


if __name__ == "__main__":
    main()
