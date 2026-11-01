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

import copy
import json
from datetime import datetime, timedelta, timezone

import pytest

from scripts.l11.debt_graph_service import ENGINE_ERROR_RULE, DebtGraphService


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


# ─────────────────────────────────────────────
# WU-27 regression (RG-36): lifecycle, JSON parity, health
# ─────────────────────────────────────────────
def _finding(file: str, rule: str = "E501", tool: str = "ruff", severity: str = "P2") -> dict:
    return {
        "tool": tool,
        "rule": rule,
        "message": f"{rule} in {file}",
        "file": file,
        "line": 1,
        "severity": severity,
    }


def _records(service: DebtGraphService) -> dict[str, dict]:
    return {r["file"]: r for r in json.loads(service._json_path.read_text())}


class TestLifecycle:
    async def test_absent_finding_in_scope_becomes_fixed_then_regressed(self, graph_service):
        a, b = _finding("core/a.py"), _finding("core/b.py")
        await graph_service.upsert_findings([a, b], scope=["core/"])
        await graph_service.upsert_findings([a], scope=["core/"])
        assert _records(graph_service)["core/b.py"]["status"] == "fixed"
        assert _records(graph_service)["core/a.py"]["status"] == "open"
        assert await graph_service.detect_regressions() == []

        await graph_service.upsert_findings([a, b], scope=["core/"])
        assert _records(graph_service)["core/b.py"]["status"] == "regressed"
        regressions = await graph_service.detect_regressions()
        assert [r["file"] for r in regressions] == ["core/b.py"]

    async def test_out_of_scope_and_unscoped_upserts_do_not_fix(self, graph_service):
        a, b = _finding("core/a.py"), _finding("api/b.py")
        await graph_service.upsert_findings([a, b], scope=["core/", "api/"])
        await graph_service.upsert_findings([], scope=["core/"])
        await graph_service.upsert_findings([])
        recs = _records(graph_service)
        assert recs["core/a.py"]["status"] == "fixed"
        assert recs["api/b.py"]["status"] == "open"

    async def test_engine_error_tool_cannot_vouch_for_absence(self, graph_service):
        a = _finding("core/a.py", tool="ruff")
        await graph_service.upsert_findings([a], scope=["core/"])
        ruff_failed = {
            "tool": "ruff",
            "rule": ENGINE_ERROR_RULE,
            "message": "ruff could not run",
            "file": "",
            "severity": "P1",
        }
        await graph_service.upsert_findings([ruff_failed], scope=["core/"])
        assert _records(graph_service)["core/a.py"]["status"] == "open"


class TestJsonParity:
    async def test_get_stats_counts_open_and_regressed(self, graph_service):
        await graph_service.upsert_findings(
            [
                _finding("core/a.py"),
                _finding("core/b.py"),
                _finding("core/c.py", severity="P1"),
                _finding("core/d.py"),
            ],
            scope=["core/"],
        )
        await graph_service.upsert_findings(
            [_finding("core/a.py"), _finding("core/b.py"), _finding("core/c.py", severity="P1")],
            scope=["core/"],
        )
        stats = await graph_service.get_stats()
        assert stats["total_open"] == 3
        assert stats["by_severity"] == {"P2": 2, "P1": 1}
        assert "timestamp" in stats

    async def test_aging_escalates_stale_open_findings(self, graph_service):
        await graph_service.upsert_findings(
            [
                _finding("core/stale_p2.py"),
                _finding("core/old_p1.py", severity="P1"),
                _finding("core/fresh.py"),
            ]
        )
        data = json.loads(graph_service._json_path.read_text())
        now = datetime.now(tz=timezone.utc)
        for rec in data:
            if rec["file"] == "core/stale_p2.py":
                rec["first_seen"] = (now - timedelta(days=40)).isoformat()
            if rec["file"] == "core/old_p1.py":
                rec["first_seen"] = (now - timedelta(days=70)).isoformat()
        graph_service._json_path.write_text(json.dumps(data))

        escalated = await graph_service.apply_aging_policy()

        recs = _records(graph_service)
        assert escalated == 2
        assert recs["core/stale_p2.py"]["severity"] == "P1"
        assert recs["core/old_p1.py"]["severity"] == "P0"
        assert recs["core/fresh.py"]["severity"] == "P2"


class TestConfiguredNeo4jHealth:
    async def test_configured_but_unavailable_neo4j_is_unhealthy(
        self, sample_config, tmp_path, monkeypatch
    ):
        for var in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"):
            monkeypatch.delenv(var, raising=False)
        config = copy.deepcopy(sample_config)
        config["state_management"]["debt_graph"]["backend"] = "neo4j"
        config["state_management"]["json_fallback"]["path"] = str(tmp_path / "d.json")
        health = await DebtGraphService(config).health()
        assert health["healthy"] is False
        assert health["backend"] == "json_fallback"
        assert health["configured_backend"] == "neo4j"


class _FakeResult:
    async def single(self):
        return {"cnt": 1}


class _FakeSession:
    def __init__(self, calls):
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def run(self, query, params=None):
        self.calls.append((query, params or {}))
        return _FakeResult()


class _FakeDriver:
    def __init__(self):
        self.calls: list = []

    def session(self):
        return _FakeSession(self.calls)


class TestNeo4jLifecycleQuery:
    async def test_scoped_upsert_issues_fix_transition(self, graph_service):
        driver = _FakeDriver()
        graph_service._driver = driver
        await graph_service.upsert_findings([_finding("core/a.py")], scope=["core/"])
        fix_calls = [(q, p) for q, p in driver.calls if "'fixed'" in q and "SET f.status" in q]
        assert len(fix_calls) == 1
        _, params = fix_calls[0]
        assert params["hashes"] == [graph_service._compute_hash(_finding("core/a.py"))]
        assert "core" in params["prefixes"]
        assert params["skip_tools"] == []
