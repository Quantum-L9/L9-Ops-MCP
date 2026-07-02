# --- L9_META ---
# l9_schema: 1
# component: test_risk_scorer
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

"""Tests for L11 Risk Scorer.

DORA:
    component_id: test-l11-risk-scorer
    tier: 2
    lifecycle: production
    owner: platform-engineering
"""
from __future__ import annotations

from scripts.l11.risk_scorer import RiskScorer


class TestRiskCalculation:
    def test_p0_core_finding_high_score(self, sample_config):
        scorer = RiskScorer(sample_config)
        finding = {
            "tool": "adr_checker",
            "rule": "ADR-0019",
            "message": "stdlib logging",
            "file": "core/kernel/engine.py",
            "severity": "P0",
        }
        score = scorer.calculate(finding)
        # P0(100)*0.4 + core(100)*0.25 + tier1(100)*0.2 + churn(50)*0.1 + no_owner(100)*0.05
        # = 40 + 25 + 20 + 5 + 5 = 95
        assert score >= 85
        assert scorer.classify(score) == "block_pr"

    def test_p3_utility_finding_low_score(self, sample_config):
        scorer = RiskScorer(sample_config)
        finding = {
            "tool": "ruff",
            "rule": "W291",
            "message": "trailing whitespace",
            "file": "scripts/utils/helper.py",
            "severity": "P3",
            "owner": "cryptoxdog",
        }
        score = scorer.calculate(finding)
        # P3(20)*0.4 + utility(40)*0.25 + tier3(20)*0.2 + churn(50)*0.1 + has_owner(0)*0.05
        # = 8 + 10 + 4 + 5 + 0 = 27
        assert score < 40
        assert scorer.classify(score) == "accept"

    def test_ownership_gap_penalty(self, sample_config):
        scorer = RiskScorer(sample_config)
        with_owner = {"severity": "P2", "file": "api/x.py", "owner": "someone"}
        without_owner = {"severity": "P2", "file": "api/x.py"}
        score_with = scorer.calculate(with_owner)
        score_without = scorer.calculate(without_owner)
        assert score_without > score_with

    def test_blast_radius_from_ai_enrichment(self, sample_config):
        scorer = RiskScorer(sample_config)
        finding = {
            "severity": "P2",
            "file": "scripts/utils.py",
            "ai_enrichment": {"blast_radius": "system-wide"},
        }
        score = scorer.calculate(finding)
        # system-wide maps to core_kernel weight (100)
        assert score > 40

    def test_classify_thresholds(self, sample_config):
        scorer = RiskScorer(sample_config)
        assert scorer.classify(90) == "block_pr"
        assert scorer.classify(85) == "block_pr"
        assert scorer.classify(70) == "create_issue"
        assert scorer.classify(50) == "backlog"
        assert scorer.classify(30) == "accept"


class TestHealth:
    def test_health_always_healthy(self, sample_config):
        scorer = RiskScorer(sample_config)
        health = scorer.health()
        assert health["healthy"] is True
        assert "thresholds" in health
