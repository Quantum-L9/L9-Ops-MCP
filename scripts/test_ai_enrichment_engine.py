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
from unittest.mock import patch

import pytest

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
            prompt = engine._build_prompt({
                "tool": "bandit",
                "rule": "B101",
                "message": "assert used",
                "severity": "P1",
                "file": "core/x.py",
            })
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
