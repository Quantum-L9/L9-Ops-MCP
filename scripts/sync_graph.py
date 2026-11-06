#!/usr/bin/env python3
# >>> l9:meta >>>
# id: L9-Ops-MCP.script.scripts_sync_graph__py
# title: sync graph
# artifact_type: script
# mcp_primitive: none
# callable: false
# retrievable: false
# injectable: false
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: scripts/sync_graph.py
# content_hash: c6aee282df9ba926ffeb54b31e3b871337676a3765099d40296b9f24bf0fa50f
# token_cost_estimate: 272
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
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
    report = sync_graph_from_index(
        args.index, args.repo_root, args.seed, args.report, args.namespace
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
