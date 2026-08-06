# --- L9_META ---
# l9_schema: 1
# component: risk_scorer
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

"""L11 Risk Scorer.

Five-factor weighted risk model:
  severity × 0.40 + blast_radius × 0.25 + criticality × 0.20
  + change_frequency × 0.10 + ownership_gap × 0.05

DORA:
    component_id: l11-risk-scorer
    tier: 2
    lifecycle: production
    owner: platform-engineering
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class RiskScorer:
    """Multi-factor risk scoring engine.

    ADR Compliance:
        ADR-0019  structlog-only logging
    """

    def __init__(self, config: dict[str, Any]) -> None:
        rm = config["risk_model"]
        self._weights = rm.get("weights", {})
        self._thresholds = rm.get("thresholds", {})

    # ── Public API ──────────────────────────
    def calculate(self, finding: dict[str, Any]) -> float:
        """Return risk score in [0, 100].

        Uses the five-factor formula from pipeline config.
        """
        sev = self._severity_score(finding)
        blast = self._blast_radius_score(finding)
        crit = self._criticality_score(finding)
        churn = self._churn_score(finding)
        own = self._ownership_gap_score(finding)

        score = round(
            sev * 0.40 + blast * 0.25 + crit * 0.20 + churn * 0.10 + own * 0.05,
            2,
        )

        logger.debug(
            "risk_calculated",
            tool=finding.get("tool"),
            file=finding.get("file"),
            score=score,
            components={
                "severity": sev,
                "blast_radius": blast,
                "criticality": crit,
                "churn": churn,
                "ownership_gap": own,
            },
        )
        return score

    def classify(self, score: float) -> str:
        """Map score to action: block_pr | create_issue | backlog | accept."""
        if score >= self._thresholds.get("block_pr", 85):
            return "block_pr"
        if score >= self._thresholds.get("create_issue", 65):
            return "create_issue"
        if score >= self._thresholds.get("backlog", 40):
            return "backlog"
        return "accept"

    # ── Factor Calculators ──────────────────
    def _severity_score(self, finding: dict[str, Any]) -> float:
        sev_map = self._weights.get("severity", {})
        severity = finding.get("severity", "P3")
        return float(sev_map.get(severity, 20))

    def _blast_radius_score(self, finding: dict[str, Any]) -> float:
        enrichment = finding.get("ai_enrichment", {})
        blast = enrichment.get("blast_radius", "")
        br_map = self._weights.get("blast_radius", {})

        if blast == "system-wide":
            return float(br_map.get("core_kernel", 100))
        if blast == "module":
            return float(br_map.get("agent_logic", 60))
        if blast == "isolated":
            return float(br_map.get("utility", 40))

        # Heuristic from file path
        file_path = finding.get("file", "")
        if "core/" in file_path or "kernel/" in file_path:
            return float(br_map.get("core_kernel", 100))
        if "api/" in file_path:
            return float(br_map.get("api_layer", 80))
        if "agents/" in file_path:
            return float(br_map.get("agent_logic", 60))
        if "workers/" in file_path:
            return float(br_map.get("worker", 50))
        return float(br_map.get("utility", 40))

    def _criticality_score(self, finding: dict[str, Any]) -> float:
        crit_map = self._weights.get("service_criticality", {})
        file_path = finding.get("file", "")
        if any(d in file_path for d in ("core/", "api/", "memory/")):
            return float(crit_map.get("tier1_production", 100))
        if any(d in file_path for d in ("agents/", "orchestrators/")):
            return float(crit_map.get("tier2_staging", 60))
        return float(crit_map.get("tier3_dev", 20))

    def _churn_score(self, finding: dict[str, Any]) -> float:
        """File change frequency (git-log derived).

        Stub returns 50.  Production: query ``git log --format=%H <file> | wc -l``.
        """
        return float(finding.get("churn", 50))

    def _ownership_gap_score(self, finding: dict[str, Any]) -> float:
        """Penalize findings without a CODEOWNER."""
        owner = finding.get("owner")
        return 0.0 if owner else 100.0

    # ── Health ──────────────────────────────
    def health(self) -> dict[str, Any]:
        """Risk scorer is stateless and always healthy."""
        return {"healthy": True, "thresholds": self._thresholds}
