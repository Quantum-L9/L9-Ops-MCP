#!/usr/bin/env python3
# --- L9_META ---
# l9_schema: 1
# component: validate_headers
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

"""
validate_headers.py — Enforce canonical headers on all kernels and skills.
Usage: python3 scripts/validate_headers.py --dir docs/kernels --ext .yaml --required title,purpose,summary,...
Relative --dir paths resolve from the repository root.
Exits 1 if any file is missing (or has an empty) required field, if a file's
metadata cannot be parsed, if --dir does not exist, or if it holds no files
with the requested extension.
"""

import argparse
import sys
from pathlib import Path

from validate_helpers import MetadataError, load_metadata, missing_fields, resolve_repo_path


def check_file(filepath: Path, required_fields: list[str]) -> list[str]:
    try:
        meta = load_metadata(filepath)
    except (MetadataError, UnicodeDecodeError) as exc:
        return [f"{filepath}: parse error: {exc}"]
    if meta is None:
        return [f"{filepath}: no metadata block"]
    if not isinstance(meta, dict):
        return [f"{filepath}: metadata is not a mapping"]
    return [f"{filepath}: missing field '{f}'" for f in missing_fields(meta, required_fields)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    parser.add_argument("--ext", default=".yaml")
    parser.add_argument("--required", required=True)
    args = parser.parse_args()

    required_fields = [f.strip() for f in args.required.split(",") if f.strip()]
    directory = resolve_repo_path(args.dir)
    if not directory.is_dir():
        print(f"  FAIL: directory not found: {directory}")
        return 1
    files = sorted(p for p in directory.rglob(f"*{args.ext}") if p.is_file())
    if not files:
        print(f"  FAIL: no *{args.ext} files under {directory}")
        return 1

    errors: list[str] = []
    for path in files:
        errors.extend(check_file(path, required_fields))

    if errors:
        for e in errors:
            print(f"  FAIL: {e}")
        return 1
    print(f"  OK: All {len(files)} files in {directory} have required headers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
