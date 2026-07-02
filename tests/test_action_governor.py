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
