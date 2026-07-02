# --- L9_META ---
# l9_schema: 1
# component: renderer
# artifact_type: runtime
# tags: [l9-action-governor, runtime]
# retrieval: on_demand
# status: active
# --- /L9_META ---

from __future__ import annotations

from .models import ActionGovernorResult, DecisionPacket


def render_decision_report(result: ActionGovernorResult) -> str:
    lines: list[str] = [
        "# L9 Action Governor Decision Report",
        "",
        "## Ranked Decisions",
        "",
    ]
    for decision in result.ranked_decisions:
        lines.extend(_decision_block(decision))
    lines.extend(
        [
            "",
            "## Queue Counts",
            "",
            f"- execution_queue: {len(result.execution_queue)}",
            f"- remediation_queue: {len(result.remediation_queue)}",
            f"- escalation_queue: {len(result.escalation_queue)}",
            f"- rename_plan: {len(result.rename_plan)}",
            f"- reorg_plan: {len(result.reorg_plan)}",
            "",
            "## Operating Rule",
            "",
            "No source files are mutated by this report. All changes require approval.",
        ]
    )
    return "\n".join(lines) + "\n"


def _decision_block(decision: DecisionPacket) -> list[str]:
    return [
        f"### {decision.rank}. {decision.canonical_name}",
        "",
        f"- decision_class: `{decision.decision_class.value}`",
        f"- priority_score: `{decision.priority_score}`",
        f"- confidence: `{decision.confidence}`",
        f"- target_folder: `{decision.target_folder}`",
        f"- reason: {decision.reason}",
        f"- next_action: {decision.next_action}",
        "",
    ]
