# --- L9_META ---
# l9_schema: 1
# component: test_debt_graph_service
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

"""Tests for L11 Debt Graph Service (JSON fallback mode).

DORA:
    component_id: test-l11-debt-graph-service
    tier: 2
    lifecycle: production
    owner: platform-engineering
"""

from __future__ import annotations

import json

import pytest

from scripts.l11.debt_graph_service import DebtGraphService


@pytest.fixture
def graph_service(sample_config, tmp_path):
    """DebtGraphService using JSON fallback (no Neo4j in tests)."""
    config = sample_config.copy()
    json_path = str(tmp_path / "debt_findings.json")
    config["state_management"]["json_fallback"]["path"] = json_path
    config["state_management"]["debt_graph"]["backend"] = "json"
    return DebtGraphService(config)


class TestUpsertFindings:
    @pytest.mark.asyncio
    async def test_upsert_creates_json_file(self, graph_service, tmp_path):
        findings = [
            {"tool": "ruff", "rule": "E501", "message": "line too long", "file": "x.py"},
        ]
        count = await graph_service.upsert_findings(findings)
        assert count == 1
        json_path = graph_service._json_path
        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert len(data) == 1
        assert data[0]["status"] == "open"

    @pytest.mark.asyncio
    async def test_upsert_deduplicates(self, graph_service):
        finding = {"tool": "ruff", "rule": "E501", "message": "x", "file": "a.py"}
        await graph_service.upsert_findings([finding])
        await graph_service.upsert_findings([finding])
        data = json.loads(graph_service._json_path.read_text())
        assert len(data) == 1  # Deduped by hash

    @pytest.mark.asyncio
    async def test_regression_detection(self, graph_service):
        finding = {"tool": "ruff", "rule": "E501", "message": "x", "file": "a.py"}
        await graph_service.upsert_findings([finding])
        # Simulate fix
        data = json.loads(graph_service._json_path.read_text())
        data[0]["status"] = "fixed"
        graph_service._json_path.write_text(json.dumps(data))
        # Re-introduce
        await graph_service.upsert_findings([finding])
        data = json.loads(graph_service._json_path.read_text())
        assert data[0]["status"] == "regressed"


class TestDetectRegressions:
    @pytest.mark.asyncio
    async def test_returns_regressed_findings(self, graph_service):
        finding = {"tool": "ruff", "rule": "E501", "message": "x", "file": "a.py"}
        await graph_service.upsert_findings([finding])
        data = json.loads(graph_service._json_path.read_text())
        data[0]["status"] = "regressed"
        graph_service._json_path.write_text(json.dumps(data))
        regressions = await graph_service.detect_regressions()
        assert len(regressions) == 1

    @pytest.mark.asyncio
    async def test_no_regressions_on_clean(self, graph_service):
        regressions = await graph_service.detect_regressions()
        assert len(regressions) == 0


class TestHash:
    def test_deterministic_hash(self, graph_service):
        finding = {"tool": "ruff", "rule": "E501", "file": "x.py", "message": "hi"}
        h1 = graph_service._compute_hash(finding)
        h2 = graph_service._compute_hash(finding)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex


class TestHealth:
    @pytest.mark.asyncio
    async def test_json_fallback_healthy(self, graph_service):
        health = await graph_service.health()
        assert health["healthy"] is True
        assert health["backend"] == "json_fallback"
