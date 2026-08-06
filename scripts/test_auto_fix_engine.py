# --- L9_META ---
# l9_schema: 1
# component: test_auto_fix_engine
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

"""Tests for L11 Auto-Fix Engine.

DORA:
    component_id: test-l11-auto-fix-engine
    tier: 3
    lifecycle: production
    owner: platform-engineering
"""

from __future__ import annotations

import pytest

from scripts.l11.auto_fix_engine import AutoFixEngine, FixResult


class TestAutoFixDisabled:
    def test_returns_disabled_when_off(self, sample_config):
        engine = AutoFixEngine(sample_config)
        assert engine.enabled is False

    @pytest.mark.asyncio
    async def test_attempt_fix_returns_disabled(self, sample_config):
        engine = AutoFixEngine(sample_config)
        result = await engine.attempt_fix({"finding_hash": "abc123"})
        assert result.success is False
        assert result.reason == "auto_fix_disabled"


class TestAutoFixEnabled:
    @pytest.fixture
    def enabled_config(self, sample_config):
        sample_config["remediation"]["auto_fix"]["enabled"] = True
        return sample_config

    @pytest.mark.asyncio
    async def test_unsupported_category_rejected(self, enabled_config):
        engine = AutoFixEngine(enabled_config)
        result = await engine.attempt_fix(
            {
                "finding_hash": "abc123",
                "category": "unknown_category",
            }
        )
        assert result.success is False
        assert "unsupported_category" in result.reason


class TestFixResult:
    def test_to_dict_serializes(self):
        result = FixResult(
            success=True,
            finding_hash="abc123",
            fix_description="ruff --fix applied",
            tests_passed=True,
            pr_url="https://github.com/cryptoxdog/L9/compare/main...auto-fix/abc123",
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["finding_hash"] == "abc123"
        assert "attempted_at" in d


class TestSupportedCategories:
    def test_supported_set_is_frozen(self):
        assert isinstance(AutoFixEngine.SUPPORTED_CATEGORIES, frozenset)
        assert "linting_errors" in AutoFixEngine.SUPPORTED_CATEGORIES
        assert "structlog_migration" in AutoFixEngine.SUPPORTED_CATEGORIES
