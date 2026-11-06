# >>> l9:meta >>>
# id: L9-Ops-MCP.source.src_l9_action_governor_cli__py
# title: cli
# artifact_type: source
# mcp_primitive: resource
# callable: false
# retrievable: true
# injectable: true
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: src/l9_action_governor/cli.py
# content_hash: 149e301c5c421f391f08a8f01e2b2955a172b599a498f3129cb3411f7efad72d
# token_cost_estimate: 276
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
# --- L9_META ---
# l9_schema: 1
# component: cli
# artifact_type: runtime
# tags: [l9-action-governor, runtime]
# retrieval: on_demand
# status: active
# --- /L9_META ---

from __future__ import annotations

import argparse
from pathlib import Path

from .loader import load_run
from .planner import ActionGovernor
from .writer import write_result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run L9 Action Governor on an L9 run folder.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    decide = subparsers.add_parser("decide", help="Generate action-governor decisions.")
    decide.add_argument("run_dir", type=Path)
    decide.add_argument("--out", type=Path, required=True)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "decide":
        graph, scores, plan, findings = load_run(args.run_dir)
        result = ActionGovernor().decide(graph, scores, plan, findings)
        write_result(result, args.out)


if __name__ == "__main__":
    main()
