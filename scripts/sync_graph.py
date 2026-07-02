#!/usr/bin/env python3
"""CLI: export, verify, and ingest graph seed records in one deterministic pass."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from l9_ops_mcp.adapters.graph_sync import sync_graph_from_index  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--seed", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--namespace", default="core")
    args = parser.parse_args()
    report = sync_graph_from_index(args.index, args.repo_root, args.seed, args.report, args.namespace)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
