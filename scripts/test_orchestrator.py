# --- L9_META ---
# l9_schema: 1
# component: test_orchestrator
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

"""Tests for L11 Orchestrator.

DORA:
    component_id: test-l11-orchestrator
    tier: 2
    lifecycle: production
    owner: platform-engineering
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from scripts.l11.orchestrator import L11Orchestrator, Finding


@pytest.fixture
def mock_engines(sample_config, tmp_path):
    """Create orchestrator with mocked engines."""
    import yaml

    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(sample_config))

    det_engine = AsyncMock()
    det_engine.scan = AsyncMock(return_value={"passed": True, "findings": []})
    det_engine.health = AsyncMock(return_value={"healthy": True})

    ai_engine = AsyncMock()
    ai_engine.health = AsyncMock(return_value={"healthy": True})

    risk_scorer = MagicMock()
    risk_scorer.calculate = MagicMock(return_value=50.0)
    risk_scorer.health = MagicMock(return_value={"healthy": True})

    debt_graph = AsyncMock()
    debt_graph.upsert_findings = AsyncMock(return_value=0)
    debt_graph.detect_regressions = AsyncMock(return_value=[])
    debt_graph.health = AsyncMock(return_value={"healthy": True})

    orch = L11Orchestrator(
        config_path=config_path,
        deterministic_engine=det_engine,
        ai_engine=ai_engine,
        risk_scorer=risk_scorer,
        debt_graph=debt_graph,
    )
    return orch


class TestPRScan:
    @pytest.mark.asyncio
    async def test_clean_pr_passes(self, mock_engines):
        result = await mock_engines.run_pr_scan(pr_number=1, changed_files=["core/x.py"])
        assert result.passed is True
        assert result.should_block_merge is False

    @pytest.mark.asyncio
    async def test_pr_with_findings(self, mock_engines):
        mock_engines.deterministic_engine.scan = AsyncMock(
            return_value={
                "passed": False,
                "findings": [
                    Finding(tool="ruff", message="error", severity="P0", file_path="x.py"),
                ],
            }
        )
        mock_engines.risk_scorer.calculate = MagicMock(return_value=90.0)
        result = await mock_engines.run_pr_scan(pr_number=2, changed_files=["x.py"])
        assert result.passed is False
        assert result.should_block_merge is True


class TestNightlyScan:
    @pytest.mark.asyncio
    async def test_nightly_returns_regressions(self, mock_engines):
        mock_engines.debt_graph.detect_regressions = AsyncMock(
            return_value=[{"file": "a.py", "message": "regressed"}]
        )
        result = await mock_engines.run_nightly_scan(scope=["core/"])
        assert len(result.regressions) == 1


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_all_healthy(self, mock_engines):
        health = await mock_engines.health_check()
        assert health["healthy"] is True
        assert "deterministic_engine" in health["components"]
