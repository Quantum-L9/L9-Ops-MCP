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

import asyncio
import copy
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from scripts.l11.ai_enrichment_engine import AIEnrichmentEngine
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


# ─────────────────────────────────────────────
# WU-21 regression (RG-22): default construction and health
# ─────────────────────────────────────────────
SHIPPED_CONFIG = Path(__file__).resolve().parent / "l11" / "pipeline_config.yaml"


class TestDefaultConstruction:
    def test_shipped_config_builds_required_engines(self):
        orch = L11Orchestrator(SHIPPED_CONFIG)
        assert isinstance(orch.deterministic_engine, DeterministicEngine)
        assert isinstance(orch.risk_scorer, RiskScorer)
        assert isinstance(orch.debt_graph, DebtGraphService)
        assert isinstance(orch.ai_engine, AIEnrichmentEngine)

    async def test_default_constructed_orchestrator_scans(
        self, real_pipeline_config, tmp_path, monkeypatch
    ):
        """subaudit_A r7: runbook usage L11Orchestrator(config) must scan."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "core").mkdir()
        (tmp_path / "core" / "a.py").write_text("import logging\n")
        orch = L11Orchestrator(_write_config(real_pipeline_config, tmp_path))
        result = await orch.run_pr_scan(pr_number=1, changed_files=["core/a.py"])
        assert result.should_block_merge is True
        assert json.loads((tmp_path / "debt.json").read_text())[0]["file"] == "core/a.py"

    def test_missing_required_engine_config_fails_at_construction(self, sample_config, tmp_path):
        cfg = copy.deepcopy(sample_config)
        del cfg["detection"]["deterministic_layer"]
        with pytest.raises(ValueError, match="deterministic_engine"):
            L11Orchestrator(_write_config(cfg, tmp_path))

    async def test_health_with_no_components_is_unhealthy(self, mock_engines):
        mock_engines.deterministic_engine = None
        mock_engines.ai_engine = None
        mock_engines.debt_graph = None
        mock_engines.risk_scorer = None
        health = await mock_engines.health_check()
        assert health["healthy"] is False
        assert set(health["missing_components"]) == {"deterministic_engine", "risk_scorer"}

    async def test_health_with_missing_required_component_is_unhealthy(self, mock_engines):
        mock_engines.risk_scorer = None
        health = await mock_engines.health_check()
        assert health["healthy"] is False
        assert health["missing_components"] == ["risk_scorer"]


# ─────────────────────────────────────────────
# WU-27 cross-component: nightly scan drives the debt lifecycle
# ─────────────────────────────────────────────
class TestNightlyLifecycle:
    async def test_nightly_scan_marks_fixed_then_regressed(
        self, real_pipeline_config, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "core").mkdir()
        target = tmp_path / "core" / "a.py"
        orch = L11Orchestrator(_write_config(real_pipeline_config, tmp_path))
        debt_file = tmp_path / "debt.json"

        target.write_text("import logging\n")
        await orch.run_nightly_scan(scope=["core/a.py"])
        assert json.loads(debt_file.read_text())[0]["status"] == "open"

        target.write_text("import structlog\n")
        await orch.run_nightly_scan(scope=["core/a.py"])
        assert json.loads(debt_file.read_text())[0]["status"] == "fixed"

        target.write_text("import logging\n")
        result = await orch.run_nightly_scan(scope=["core/a.py"])
        assert json.loads(debt_file.read_text())[0]["status"] == "regressed"
        assert [r["file"] for r in result.regressions] == ["core/a.py"]


# ─────────────────────────────────────────────
# WU-22 regression (RG-23): async enrichment actually completes
# ─────────────────────────────────────────────
class _SlowEnricher:
    """In-process fake of AIEnrichmentEngine.enqueue_enrichment."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.started = False
        self.finished = False

    async def enqueue_enrichment(self, findings):
        self.started = True
        await asyncio.sleep(0.05)
        if self.fail:
            msg = "enrichment backend down"
            raise RuntimeError(msg)
        for f in findings:
            f["ai_enrichment"] = {"category": "maintainability"}
        self.finished = True

    async def health(self):
        return {"healthy": True}


def _async_enrichment_orchestrator(sample_config, tmp_path, enricher):
    cfg = copy.deepcopy(sample_config)
    cfg["execution"]["triggers"]["pr"]["ai_enrichment_async"] = True
    det = AsyncMock()
    det.scan = AsyncMock(
        return_value={
            "passed": False,
            "findings": [
                {
                    "tool": "ruff",
                    "rule": "E1",
                    "message": "m",
                    "file": "core/a.py",
                    "severity": "P0",
                }
            ],
        }
    )
    cfg["state_management"]["json_fallback"]["path"] = str(tmp_path / "debt.json")
    return L11Orchestrator(
        _write_config(cfg, tmp_path),
        deterministic_engine=det,
        risk_scorer=RiskScorer(cfg),
        ai_engine=enricher,
    )


class TestAsyncEnrichment:
    def test_enrichment_finishes_before_loop_shutdown(self, sample_config, tmp_path):
        """subaudit_A r3: asyncio.run(run_pr_scan) must not cancel enrichment."""
        enricher = _SlowEnricher()
        orch = _async_enrichment_orchestrator(sample_config, tmp_path, enricher)
        result = asyncio.run(orch.run_pr_scan(pr_number=3, changed_files=["core/a.py"]))
        assert result.enrichment_queued is True
        assert enricher.finished is True
        assert result.enrichment_completed is True
        assert result.findings[0].ai_enrichment == {"category": "maintainability"}

    def test_enrichment_failure_is_observed_and_does_not_change_decision(
        self, sample_config, tmp_path
    ):
        enricher = _SlowEnricher(fail=True)
        orch = _async_enrichment_orchestrator(sample_config, tmp_path, enricher)
        result = asyncio.run(orch.run_pr_scan(pr_number=4, changed_files=["core/a.py"]))
        assert enricher.started is True
        assert result.should_block_merge is True
        assert result.enrichment_completed is False
        assert result.enrichment_error == "RuntimeError: enrichment backend down"
