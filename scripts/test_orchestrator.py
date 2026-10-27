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

import copy
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from scripts.l11.debt_graph_service import DebtGraphService
from scripts.l11.deterministic_engine import DeterministicEngine
from scripts.l11.orchestrator import Finding, L11Orchestrator
from scripts.l11.risk_scorer import RiskScorer


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
                    {
                        "tool": "ruff",
                        "rule": "E999",
                        "message": "error",
                        "severity": "P0",
                        "file": "x.py",
                        "line": 1,
                    },
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


# ─────────────────────────────────────────────
# WU-20 regression (RG-20): real producer contract end to end
# ─────────────────────────────────────────────
def _write_config(config: dict, tmp_path: Path) -> Path:
    import yaml

    config_path = tmp_path / "l11_config.yaml"
    config_path.write_text(yaml.dump(config))
    return config_path


@pytest.fixture
def real_pipeline_config(sample_config, tmp_path):
    """Config that runs only the offline ADR engine and a JSON debt store."""
    cfg = copy.deepcopy(sample_config)
    cfg["detection"]["deterministic_layer"]["engines"] = [
        {"name": "adr_compliance", "enabled": True},
    ]
    cfg["state_management"]["json_fallback"]["path"] = str(tmp_path / "debt.json")
    return cfg


class TestFindingContract:
    def test_from_producer_dict_round_trips_producer_keys(self):
        producer = {
            "tool": "ruff",
            "rule": "E501",
            "message": "Line too long",
            "file": "core/kernel/engine.py",
            "line": 7,
            "severity": "P2",
        }
        finding = Finding.from_dict(producer)
        out = finding.to_dict()
        for key, value in producer.items():
            assert out[key] == value
        assert "file_path" not in out

    def test_malformed_producer_finding_raises_value_error(self):
        with pytest.raises(ValueError, match="severity"):
            Finding.from_dict({"tool": "ruff", "message": "x"})
        with pytest.raises(ValueError, match="mapping"):
            Finding.from_dict(["not", "a", "dict"])  # type: ignore[arg-type]


class TestRealProducerPipeline:
    async def test_pr_scan_with_real_engine_blocks_p0_in_core(
        self, real_pipeline_config, tmp_path, monkeypatch
    ):
        """subaudit_A r1/r2: real engine -> real scorer -> real debt graph."""
        monkeypatch.chdir(tmp_path)
        core = tmp_path / "core"
        core.mkdir()
        (core / "a.py").write_text("import logging\n")
        (core / "b.py").write_text("import logging\n")

        orch = L11Orchestrator(
            _write_config(real_pipeline_config, tmp_path),
            deterministic_engine=DeterministicEngine(real_pipeline_config),
            risk_scorer=RiskScorer(real_pipeline_config),
            debt_graph=DebtGraphService(real_pipeline_config),
        )
        result = await orch.run_pr_scan(pr_number=7, changed_files=["core/a.py", "core/b.py"])

        assert result.passed is False
        assert result.should_block_merge is True
        assert {f.file for f in result.findings} == {"core/a.py", "core/b.py"}
        assert all(f.rule == "ADR-0019" for f in result.findings)

        records = json.loads((tmp_path / "debt.json").read_text())
        assert len(records) == 2
        assert {r["file"] for r in records} == {"core/a.py", "core/b.py"}

    async def test_same_message_in_two_files_keeps_two_debt_records(
        self, real_pipeline_config, tmp_path
    ):
        """Dedup key is tool+rule+file+message: two files must not collapse."""
        producer_findings = [
            {
                "tool": "ruff",
                "rule": "E501",
                "message": "Line too long",
                "file": name,
                "line": 1,
                "severity": "P0",
            }
            for name in ("core/one.py", "core/two.py")
        ]
        det = AsyncMock()
        det.scan = AsyncMock(return_value={"passed": False, "findings": producer_findings})
        orch = L11Orchestrator(
            _write_config(real_pipeline_config, tmp_path),
            deterministic_engine=det,
            risk_scorer=RiskScorer(real_pipeline_config),
            debt_graph=DebtGraphService(real_pipeline_config),
        )
        result = await orch.run_pr_scan(pr_number=8, changed_files=["core/one.py"])

        assert result.should_block_merge is True
        assert all(f.risk_score >= 85 for f in result.findings)
        records = json.loads((tmp_path / "debt.json").read_text())
        assert len(records) == 2
        assert {r["file"] for r in records} == {"core/one.py", "core/two.py"}
        assert {r["rule"] for r in records} == {"E501"}

    async def test_malformed_producer_finding_is_reported_not_raised(
        self, real_pipeline_config, tmp_path
    ):
        det = AsyncMock()
        det.scan = AsyncMock(
            return_value={"passed": True, "findings": ["garbage", {"tool": "ruff"}]}
        )
        orch = L11Orchestrator(
            _write_config(real_pipeline_config, tmp_path),
            deterministic_engine=det,
            risk_scorer=RiskScorer(real_pipeline_config),
            debt_graph=DebtGraphService(real_pipeline_config),
        )
        result = await orch.run_pr_scan(pr_number=9, changed_files=["x.py"])

        assert result.passed is False
        assert len(result.findings) == 2
        assert all(f.rule == "malformed_finding" for f in result.findings)

    async def test_nightly_scan_with_real_engine(self, real_pipeline_config, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        core = tmp_path / "core"
        core.mkdir()
        (core / "a.py").write_text("import logging\n")
        orch = L11Orchestrator(
            _write_config(real_pipeline_config, tmp_path),
            deterministic_engine=DeterministicEngine(real_pipeline_config),
            risk_scorer=RiskScorer(real_pipeline_config),
            debt_graph=DebtGraphService(real_pipeline_config),
        )
        result = await orch.run_nightly_scan(scope=["core/a.py"])
        assert result.passed is False
        assert [f.file for f in result.findings] == ["core/a.py"]
