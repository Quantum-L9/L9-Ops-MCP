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
