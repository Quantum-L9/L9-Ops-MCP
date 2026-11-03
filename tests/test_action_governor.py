# >>> l9:meta >>>
# id: L9-Ops-MCP.test.tests_test_action_governor__py
# title: test action governor
# artifact_type: test
# mcp_primitive: none
# callable: false
# retrievable: false
# injectable: false
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: tests/test_action_governor.py
# content_hash: 53faef1944bf251a6ba244183d2f8bc2577e79bca5da9007e8e9b2bcd442f20b
# token_cost_estimate: 172
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
# --- L9_META ---
# l9_schema: 1
# component: test_action_governor
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

from pathlib import Path

from l9_action_governor.loader import load_run
from l9_action_governor.planner import ActionGovernor


def test_action_governor_produces_ranked_decisions() -> None:
    run_dir = Path("examples/l9_runs/example_run")
    graph, scores, plan, findings = load_run(run_dir)
    result = ActionGovernor().decide(graph, scores, plan, findings)
    assert result.ranked_decisions
    assert result.ranked_decisions[0].rank == 1
    assert result.execution_queue
    assert result.escalation_queue
