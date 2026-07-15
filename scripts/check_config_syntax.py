# --- L9_META ---
# l9_schema: 1
# component: check_config_syntax
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

#!/usr/bin/env python3
"""
l9-ops: Config Syntax Validator

Parse every YAML and JSON file in the repo to catch malformed config before it
reaches the governance scripts (which are driven by kernels + MANIFEST.json).
Syntax-only — does not enforce style. Exits 1 if any file fails to parse.

Usage:
    python3 scripts/check_config_syntax.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", "dist", "build"}


def iter_files(suffixes: tuple[str, ...]):
    for path in REPO_ROOT.rglob("*"):
        if path.suffix not in suffixes or not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(REPO_ROOT).parts):
            continue
        yield path


def main() -> int:
    failures: list[str] = []
    yaml_count = json_count = 0

    for path in iter_files((".yaml", ".yml")):
        yaml_count += 1
        try:
            list(yaml.safe_load_all(path.read_text()))
        except Exception as e:  # noqa: BLE001 - report any parse failure
            failures.append(f"YAML {path.relative_to(REPO_ROOT)}: {e}")

    for path in iter_files((".json",)):
        json_count += 1
        try:
            json.loads(path.read_text())
        except Exception as e:  # noqa: BLE001 - report any parse failure
            failures.append(f"JSON {path.relative_to(REPO_ROOT)}: {e}")

    print(f"Checked {yaml_count} YAML and {json_count} JSON file(s).")
    if failures:
        print(f"\n{len(failures)} file(s) failed to parse:")
        for f in failures:
            print(f"  ✗ {f}")
        return 1
    print("All config files parse cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
