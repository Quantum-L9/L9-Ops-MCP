# --- L9_META ---
# l9_schema: 1
# component: test_ai_enrichment_engine
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

"""Tests for L11 AI Enrichment Engine.

DORA:
    component_id: test-l11-ai-enrichment-engine
    tier: 2
    lifecycle: production
    owner: platform-engineering
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import httpx
import pytest

from scripts.l11 import ai_enrichment_engine as ai_module
from scripts.l11.ai_enrichment_engine import AIEnrichmentEngine, CircuitBreaker


@pytest.fixture
def ai_config(sample_config):
    """Config with AI layer."""
    sample_config["detection"]["ai_layer"] = {
        "model": "sonar-pro",
        "api_key_env": "PERPLEXITY_API_KEY",
        "circuit_breaker": {"failure_threshold": 3, "cooldown_seconds": 10},
        "retry_policy": {"max_attempts": 2},
        "cost_control": {"rate_limit_rpm": 60},
        "chunking": {"max_tokens": 2500},
    }
    return sample_config


class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker(threshold=3, cooldown=10)
        assert cb.is_open() is False
        assert cb.state == "closed"

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(threshold=2, cooldown=300)
        cb.record_failure()
        assert cb.is_open() is False
        cb.record_failure()
        assert cb.is_open() is True
        assert cb.state == "open"

    def test_resets_on_success(self):
        cb = CircuitBreaker(threshold=2, cooldown=300)
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == "closed"


class TestAIEnrichmentEngine:
    def test_init_without_api_key(self, ai_config):
        with patch.dict(os.environ, {}, clear=True):
            engine = AIEnrichmentEngine(ai_config)
            assert engine.api_key is None

    @pytest.mark.asyncio
    async def test_enrich_skips_without_api_key(self, ai_config):
        with patch.dict(os.environ, {}, clear=True):
            engine = AIEnrichmentEngine(ai_config)
            findings = [{"tool": "ruff", "message": "x"}]
            result = await engine.enrich_batch(findings)
            assert result == findings  # Returned unchanged

    @pytest.mark.asyncio
    async def test_enrich_skips_on_circuit_open(self, ai_config):
        with patch.dict(os.environ, {"PERPLEXITY_API_KEY": "test-key"}):
            engine = AIEnrichmentEngine(ai_config)
            # Force circuit open
            for _ in range(5):
                engine.circuit_breaker.record_failure()
            findings = [{"tool": "ruff", "message": "x"}]
            result = await engine.enrich_batch(findings)
            assert result == findings  # Returned unchanged


class TestPromptBuilding:
    def test_build_prompt_contains_finding_data(self, ai_config):
        with patch.dict(os.environ, {"PERPLEXITY_API_KEY": "test-key"}):
            engine = AIEnrichmentEngine(ai_config)
            prompt = engine._build_prompt(
                {
                    "tool": "bandit",
                    "rule": "B101",
                    "message": "assert used",
                    "severity": "P1",
                    "file": "core/x.py",
                }
            )
            assert "bandit" in prompt
            assert "B101" in prompt
            assert "core/x.py" in prompt


class TestResponseParsing:
    def test_parses_json_response(self, ai_config):
        with patch.dict(os.environ, {"PERPLEXITY_API_KEY": "test-key"}):
            engine = AIEnrichmentEngine(ai_config)
            content = '{"category": "security", "blast_radius": "module", "remediation": "fix it"}'
            result = engine._parse_ai_response(content)
            assert result["category"] == "security"

    def test_heuristic_fallback(self, ai_config):
        with patch.dict(os.environ, {"PERPLEXITY_API_KEY": "test-key"}):
            engine = AIEnrichmentEngine(ai_config)
            content = "This is a security issue affecting the whole system."
            result = engine._parse_ai_response(content)
            assert result["category"] == "security"
            assert result["blast_radius"] == "system-wide"


class TestHealth:
    @pytest.mark.asyncio
    async def test_healthy_when_circuit_closed(self, ai_config):
        with patch.dict(os.environ, {"PERPLEXITY_API_KEY": "test-key"}):
            engine = AIEnrichmentEngine(ai_config)
            health = await engine.health()
            assert health["healthy"] is True
            assert health["api_key_configured"] is True


# ─────────────────────────────────────────────
# WU-23 regression (RG-24): fallback on every failure, per-call breaker
# ─────────────────────────────────────────────
_REAL_ASYNC_CLIENT = httpx.AsyncClient


def _install_transport(monkeypatch, handler) -> list[httpx.Request]:
    """Route the engine's AsyncClient through an in-process MockTransport."""
    calls: list[httpx.Request] = []

    def recording(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return handler(request)

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(recording)
        return _REAL_ASYNC_CLIENT(*args, **kwargs)

    monkeypatch.setattr(ai_module.httpx, "AsyncClient", factory)
    return calls


def _connect_error(request: httpx.Request) -> httpx.Response:
    msg = "connection refused"
    raise httpx.ConnectError(msg, request=request)


@pytest.fixture
def keyed_engine(ai_config, monkeypatch):
    monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
    return AIEnrichmentEngine(ai_config)


class TestFallbackOnFailure:
    @pytest.mark.parametrize(
        "handler",
        [
            pytest.param(_connect_error, id="a-connect-error"),
            pytest.param(
                lambda r: httpx.Response(200, text="<html>not json</html>"), id="b-non-json"
            ),
            pytest.param(lambda r: httpx.Response(200, json={"choices": []}), id="c-empty-choices"),
        ],
    )
    async def test_failure_returns_fallback_and_records_breaker_failure(
        self, keyed_engine, monkeypatch, handler
    ):
        calls = _install_transport(monkeypatch, handler)
        findings = [{"tool": "ruff", "rule": "E1", "message": "x", "file": "a.py"}]
        result = await keyed_engine.enrich_batch(findings)
        assert len(result) == 1
        assert result[0]["ai_enrichment"]["enriched"] is False
        assert len(calls) == keyed_engine.max_attempts
        assert keyed_engine.circuit_breaker.failure_count == 1

    async def test_successful_call_is_marked_enriched(self, keyed_engine, monkeypatch):
        body = {"choices": [{"message": {"content": '{"category": "security"}'}}]}
        _install_transport(monkeypatch, lambda r: httpx.Response(200, json=body))
        result = await keyed_engine.enrich_batch([{"tool": "ruff", "message": "x"}])
        assert result[0]["ai_enrichment"]["enriched"] is True
        assert result[0]["ai_enrichment"]["category"] == "security"

    async def test_breaker_checked_before_each_call(self, ai_config, monkeypatch):
        """subaudit_A r4 d: threshold=1, 5 findings, 2 attempts -> no calls once open."""
        ai_config["detection"]["ai_layer"]["circuit_breaker"]["failure_threshold"] = 1
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        engine = AIEnrichmentEngine(ai_config)
        calls = _install_transport(monkeypatch, _connect_error)
        findings = [{"tool": "ruff", "message": str(i)} for i in range(5)]
        result = await engine.enrich_batch(findings)
        assert len(calls) <= engine.max_attempts
        assert engine.circuit_breaker.state == "open"
        assert all(f["ai_enrichment"]["enriched"] is False for f in result)


class TestBreakerState:
    def test_state_is_closed_below_threshold(self):
        """subaudit_A r8: 1 of 3 failures is still closed."""
        cb = CircuitBreaker(threshold=3, cooldown=10)
        cb.record_failure()
        assert cb.state == "closed"
        assert cb.is_open() is False

    def test_reading_state_has_no_side_effects(self):
        cb = CircuitBreaker(threshold=2, cooldown=0)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "half-open"
        assert cb.is_open() is False
        assert cb.failure_count == 2
        assert cb.state == "half-open"

    def test_half_open_trial_failure_reopens(self):
        cb = CircuitBreaker(threshold=2, cooldown=300)
        cb.record_failure()
        cb.record_failure()
        cb.last_failure_time = datetime.now(tz=timezone.utc) - timedelta(seconds=301)
        assert cb.state == "half-open"
        cb.record_failure()
        assert cb.state == "open"
