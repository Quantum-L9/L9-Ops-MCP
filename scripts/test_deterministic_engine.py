# --- L9_META ---
# l9_schema: 1
# component: test_deterministic_engine
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

"""Tests for L11 Deterministic Engine.

DORA:
    component_id: test-l11-deterministic-engine
    tier: 2
    lifecycle: production
    owner: platform-engineering
"""
from __future__ import annotations

import pytest

from scripts.l11.deterministic_engine import DeterministicEngine


class TestEngineInit:
    def test_engines_loaded(self, sample_config):
        engine = DeterministicEngine(sample_config)
        assert engine._is_enabled("ruff") is True
        assert engine._is_enabled("mypy") is True
        assert engine._is_enabled("nonexistent") is False

    def test_disabled_engine(self):
        cfg = {
            "detection": {
                "deterministic_layer": {
                    "engines": [{"name": "ruff", "enabled": False}],
                }
            }
        }
        engine = DeterministicEngine(cfg)
        assert engine._is_enabled("ruff") is False

    def test_semgrep_path_resolution(self, sample_config):
        engine = DeterministicEngine(sample_config)
        path = engine._resolve_semgrep_path()
        # Returns configured path or fallback — never empty
        assert isinstance(path, str)
        assert len(path) > 0


class TestADRCompliance:
    def test_detects_stdlib_logging(self, sample_config, tmp_path):
        engine = DeterministicEngine(sample_config)
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("import logging\nlogger = logging.getLogger(__name__)\n")
        findings = engine._check_adr_compliance([str(bad_file)])
        assert any(f["rule"] == "ADR-0019" for f in findings)
        assert any(f["severity"] == "P0" for f in findings)

    def test_detects_print_statement(self, sample_config, tmp_path):
        engine = DeterministicEngine(sample_config)
        bad_file = tmp_path / "prints.py"
        bad_file.write_text('print("debug output")\n')
        findings = engine._check_adr_compliance([str(bad_file)])
        assert any(
            f["rule"] == "ADR-0019" and "print()" in f["message"]
            for f in findings
        )

    def test_detects_naive_datetime(self, sample_config, tmp_path):
        engine = DeterministicEngine(sample_config)
        bad_file = tmp_path / "naive.py"
        bad_file.write_text(
            "from datetime import datetime\n"
            "def f():\n"
            "    return datetime.now()\n"
        )
        findings = engine._check_adr_compliance([str(bad_file)])
        assert any(f["rule"] == "ADR-0083" for f in findings)

    def test_passes_clean_file(self, sample_config, tmp_path):
        engine = DeterministicEngine(sample_config)
        good_file = tmp_path / "good.py"
        good_file.write_text(
            '"""Module.\n\nDORA:\n    component_id: test\n"""\n'
            "import structlog\n"
            "logger = structlog.get_logger(__name__)\n"
        )
        findings = engine._check_adr_compliance([str(good_file)])
        assert len(findings) == 0

    def test_detects_missing_dora_block(self, sample_config, tmp_path):
        engine = DeterministicEngine(sample_config)
        bad_file = tmp_path / "no_dora.py"
        bad_file.write_text("import structlog\ndef my_func():\n    pass\n")
        findings = engine._check_adr_compliance([str(bad_file)])
        assert any(f["rule"] == "ADR-0014" for f in findings)


class TestScanIntegration:
    @pytest.mark.asyncio
    async def test_scan_empty_returns_passed(self, sample_config):
        engine = DeterministicEngine(sample_config)
        result = await engine.scan([])
        assert result["passed"] is True
        assert result["findings"] == []


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_returns_enabled_engines(self, sample_config):
        engine = DeterministicEngine(sample_config)
        health = await engine.health()
        assert health["healthy"] is True
        assert "ruff" in health["engines_enabled"]
        assert isinstance(health["l9_ci_scripts_count"], int)
