# >>> l9:meta >>>
# id: L9-Ops-MCP.script.scripts_harvest_audit__py
# title: harvest audit
# artifact_type: script
# mcp_primitive: none
# callable: false
# retrievable: false
# injectable: false
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: scripts/harvest_audit.py
# content_hash: 20d69aa9853414ba6eb73e168e15371e669dd92eb3a6047b71bf652a69a5979d
# token_cost_estimate: 429
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
# --- L9_META ---
# l9_schema: 1
# component: harvest_audit
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

#!/usr/bin/env python3
"""
harvest_audit.py — IgorOS source-to-pack alignment audit.
Checks that a transformed pack file covers the required fields from its source.
Usage: python3 scripts/harvest_audit.py --source <file> --check-fields field1,field2,...
"""

import sys
import os
import argparse
import yaml


def load_frontmatter(filepath):
    with open(filepath) as f:
        content = f.read()
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                return yaml.safe_load(parts[1]) or {}
            except Exception:
                pass
    try:
        return yaml.safe_load(open(filepath)) or {}
    except Exception:
        return {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="Path to the transformed pack file")
    parser.add_argument("--check-fields", required=True, help="Comma-separated required fields")
    args = parser.parse_args()

    if not os.path.exists(args.source):
        print(f"  SKIP: {args.source} not found (not yet created)")
        sys.exit(0)

    required = [f.strip() for f in args.check_fields.split(",")]
    meta = load_frontmatter(args.source)

    missing = [f for f in required if f not in meta and f not in open(args.source).read()]
    if missing:
        print(f"  FAIL: {args.source} missing coverage for: {missing}")
        sys.exit(1)
    else:
        print(f"  OK: {args.source} covers all required fields.")


if __name__ == "__main__":
    main()
