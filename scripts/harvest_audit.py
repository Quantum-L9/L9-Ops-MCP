#!/usr/bin/env python3
# --- L9_META ---
# l9_schema: 1
# component: harvest_audit
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

"""
harvest_audit.py — IgorOS source-to-pack alignment audit.
Checks that a transformed pack file covers the required fields from its source.
Coverage means the field is a key of the file's parsed metadata (frontmatter,
L9_META block or YAML mapping); a mention in prose or a comment does not count.
Usage: python3 scripts/harvest_audit.py --source <file> --check-fields field1,field2,...
Relative --source paths resolve from the repository root.
Exits 1 when the source is missing or unparseable, or a field is not covered.
"""

import argparse
import sys

from validate_helpers import MetadataError, load_metadata, resolve_repo_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="Path to the transformed pack file")
    parser.add_argument("--check-fields", required=True, help="Comma-separated required fields")
    args = parser.parse_args()

    source = resolve_repo_path(args.source)
    if not source.is_file():
        print(f"  FAIL: {source} not found")
        return 1

    required = [f.strip() for f in args.check_fields.split(",") if f.strip()]
    try:
        meta = load_metadata(source)
    except (MetadataError, UnicodeDecodeError) as exc:
        print(f"  FAIL: {source} metadata does not parse: {exc}")
        return 1
    if not isinstance(meta, dict):
        print(f"  FAIL: {source} has no metadata mapping")
        return 1

    missing = [field for field in required if field not in meta]
    if missing:
        print(f"  FAIL: {source} missing coverage for: {missing}")
        return 1
    print(f"  OK: {source} covers all required fields.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
