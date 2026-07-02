# --- L9_META ---
# l9_schema: 1
# component: scorer
# artifact_type: runtime
# tags: [l9-action-governor, runtime]
# retrieval: on_demand
# status: active
# --- /L9_META ---

from __future__ import annotations

from .models import ComponentScore, RuntimeFinding

SEVERITY_WEIGHT: dict[str, int] = {
    "critical": 100,
    "high": 75,
    "medium": 45,
    "low": 20,
}


def clamp(value: float, lower: int = 0, upper: int = 100) -> int:
    return max(lower, min(upper, round(value)))


def runtime_urgency(findings: list[RuntimeFinding]) -> int:
    if not findings:
        return 0
    return max(SEVERITY_WEIGHT[finding.severity] for finding in findings)


def convergence_leverage(priority: str) -> int:
    return {
        "critical": 100,
        "high": 75,
        "medium": 50,
        "low": 25,
    }.get(priority, 35)


def priority_score(
    score: ComponentScore,
    findings: list[RuntimeFinding],
    convergence_priority: str,
    blocker_count: int,
) -> int:
    raw = (
        score.strategic_value * 2.0
        + score.governance_criticality * 1.7
        + score.reuse_potential * 1.4
        + score.execution_readiness * 1.2
        + runtime_urgency(findings) * 1.6
        + convergence_leverage(convergence_priority) * 1.5
        - score.entropy_risk * 1.3
        - blocker_count * 12.0
        - score.drift_risk * 0.8
    )
    normalized = raw / 7.6
    return clamp(normalized)
