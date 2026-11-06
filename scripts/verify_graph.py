#!/usr/bin/env python3
# >>> l9:meta >>>
# id: L9-Ops-MCP.script.scripts_verify_graph__py
# title: verify graph
# artifact_type: script
# mcp_primitive: none
# callable: false
# retrievable: false
# injectable: false
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: scripts/verify_graph.py
# content_hash: bb7dacdc41bc6dd1ccd06beed0c7160a6c070010689338d4b110283c1d090821
# token_cost_estimate: 185
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
"""CLI: verify graph-seed JSONL contract compliance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from l9_ops_mcp.adapters.graph_export import verify_graph_seed  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", required=True, type=Path)
    args = parser.parse_args()
    report = verify_graph_seed(args.seed)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
