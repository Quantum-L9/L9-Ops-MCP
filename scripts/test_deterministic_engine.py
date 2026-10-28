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

import copy
import json
import subprocess
from pathlib import Path

import pytest
import yaml

from scripts.l11 import deterministic_engine as de
from scripts.l11.deterministic_engine import ENGINE_ERROR_RULE, DeterministicEngine


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
        assert any(f["rule"] == "ADR-0019" and "print()" in f["message"] for f in findings)

    def test_detects_naive_datetime(self, sample_config, tmp_path):
        engine = DeterministicEngine(sample_config)
        bad_file = tmp_path / "naive.py"
        bad_file.write_text("from datetime import datetime\ndef f():\n    return datetime.now()\n")
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


# ─────────────────────────────────────────────
# WU-24 regression (RG-27): fail closed, isolate engine failures
# ─────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
SHIPPED_CONFIG = REPO_ROOT / "scripts" / "l11" / "pipeline_config.yaml"


def _config_with(sample_config, *engines: str, **layer_overrides) -> dict:
    cfg = copy.deepcopy(sample_config)
    layer = cfg["detection"]["deterministic_layer"]
    layer["engines"] = [{"name": name, "enabled": True} for name in engines]
    layer.update(layer_overrides)
    return cfg


def _fake_run(responses: dict):
    """Fake subprocess.run keyed by argv[0]; a value may be an exception to raise."""

    def run(cmd, **kwargs):
        outcome = responses[cmd[0]]
        if isinstance(outcome, BaseException):
            raise outcome
        rc, stdout, stderr = outcome
        return subprocess.CompletedProcess(cmd, rc, stdout=stdout, stderr=stderr)

    return run


def _engine_errors(result: dict, tool: str) -> list[dict]:
    return [f for f in result["findings"] if f["tool"] == tool and f["rule"] == ENGINE_ERROR_RULE]


class TestFailClosed:
    async def test_a_missing_configured_ci_script_fails(self, sample_config, tmp_path):
        missing = str(tmp_path / "ci" / "check_x.py")
        cfg = _config_with(sample_config, l9_ci_scripts={"enabled": True, "scripts": [missing]})
        result = await DeterministicEngine(cfg).scan(["a.py"])
        assert result["passed"] is False
        assert _engine_errors(result, "l9_ci_script")[0]["file"] == missing

    async def test_b_ruff_abnormal_exit_without_output_fails(self, sample_config, monkeypatch):
        monkeypatch.setattr(de.subprocess, "run", _fake_run({"ruff": (2, "", "ruff: bad config")}))
        result = await DeterministicEngine(_config_with(sample_config, "ruff")).scan(["a.py"])
        assert result["passed"] is False
        assert "bad config" in _engine_errors(result, "ruff")[0]["message"]

    async def test_c_missing_tool_binary_is_a_finding_not_a_crash(
        self, sample_config, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(de.subprocess, "run", _fake_run({"ruff": FileNotFoundError("ruff")}))
        bad = tmp_path / "bad.py"
        bad.write_text("import logging\n")
        cfg = _config_with(sample_config, "ruff", "adr_compliance")
        result = await DeterministicEngine(cfg).scan([str(bad)])
        assert result["passed"] is False
        assert len(_engine_errors(result, "ruff")) == 1
        # The other engine still ran.
        assert any(f["rule"] == "ADR-0019" for f in result["findings"])

    async def test_d_radon_error_object_is_a_finding_not_a_crash(self, sample_config, monkeypatch):
        radon_out = json.dumps({"a.py": {"error": "invalid syntax (<unknown>, line 1)"}})
        monkeypatch.setattr(de.subprocess, "run", _fake_run({"radon": (0, radon_out, "")}))
        result = await DeterministicEngine(
            _config_with(sample_config, "complexity_threshold")
        ).scan(["a.py"])
        assert result["passed"] is False
        err = _engine_errors(result, "radon")[0]
        assert err["file"] == "a.py"
        assert "invalid syntax" in err["message"]

    async def test_e_mypy_fatal_exit_fails(self, sample_config, monkeypatch):
        monkeypatch.setattr(
            de.subprocess, "run", _fake_run({"mypy": (2, "", "mypy: error: unrecognized")})
        )
        result = await DeterministicEngine(_config_with(sample_config, "mypy")).scan(["a.py"])
        assert result["passed"] is False
        assert _engine_errors(result, "mypy")

    async def test_f_directory_scope_runs_adr_checks(self, sample_config, tmp_path):
        pkg = tmp_path / "pkg" / "sub"
        pkg.mkdir(parents=True)
        (pkg / "mod.py").write_text("import logging\n")
        cfg = _config_with(sample_config, "adr_compliance")
        result = await DeterministicEngine(cfg).scan([str(tmp_path / "pkg")])
        assert result["passed"] is False
        assert [f["file"] for f in result["findings"] if f["rule"] == "ADR-0019"] == [
            str(pkg / "mod.py")
        ]

    async def test_tool_timeout_is_a_failing_finding(self, sample_config, monkeypatch):
        monkeypatch.setattr(
            de.subprocess,
            "run",
            _fake_run({"semgrep": subprocess.TimeoutExpired(["semgrep"], 5)}),
        )
        result = await DeterministicEngine(_config_with(sample_config, "semgrep")).scan(["a.py"])
        assert result["passed"] is False
        assert "TimeoutExpired" in _engine_errors(result, "semgrep")[0]["message"]

    async def test_semgrep_unparseable_output_fails(self, sample_config, monkeypatch):
        monkeypatch.setattr(de.subprocess, "run", _fake_run({"semgrep": (2, "Traceback", "")}))
        result = await DeterministicEngine(_config_with(sample_config, "semgrep")).scan(["a.py"])
        assert result["passed"] is False
        assert _engine_errors(result, "semgrep")

    async def test_clean_tool_runs_still_pass(self, sample_config, monkeypatch):
        monkeypatch.setattr(
            de.subprocess,
            "run",
            _fake_run(
                {
                    "ruff": (0, "[]", ""),
                    "mypy": (0, "", ""),
                    "bandit": (0, json.dumps({"results": [], "errors": []}), ""),
                    "semgrep": (0, json.dumps({"results": [], "errors": []}), ""),
                    "radon": (0, json.dumps({"a.py": []}), ""),
                }
            ),
        )
        cfg = _config_with(
            sample_config, "ruff", "mypy", "bandit", "semgrep", "complexity_threshold"
        )
        result = await DeterministicEngine(cfg).scan(["a.py"])
        assert result == {"passed": True, "findings": []}


class TestShippedConfig:
    def test_configured_ci_scripts_exist_or_block_is_disabled(self):
        """D-07 A: the foreign ci/ script block must not be enabled here."""
        cfg = yaml.safe_load(SHIPPED_CONFIG.read_text())
        block = cfg["detection"]["deterministic_layer"].get("l9_ci_scripts", {})
        if block.get("enabled"):
            missing = [s for s in block.get("scripts", []) if not (REPO_ROOT / s).exists()]
            assert missing == []


# ─────────────────────────────────────────────
# WU-25 regression (RG-29): ADR checks from syntax, not text
# ─────────────────────────────────────────────
DORA_HEADER = '"""Module.\n\nDORA:\n    component_id: test\n"""\n'


def _adr(sample_config, tmp_path, source: str, name: str = "mod.py") -> list[dict]:
    target = tmp_path / name
    target.write_text(DORA_HEADER + source)
    return DeterministicEngine(sample_config)._check_adr_compliance([str(target)])


class TestADRPrecision:
    @pytest.mark.parametrize(
        "source",
        [
            pytest.param("import logging_helpers\n", id="prefix-module"),
            pytest.param("import logging_helpers as lh\nlh.setup()\n", id="prefix-alias"),
            pytest.param('HINT = "use logging.getLogger never"\n', id="string-literal"),
            pytest.param("# logging.getLogger is banned\nx = 1\n", id="comment"),
            pytest.param("import structlog\nlog = structlog.getLogger()\n", id="structlog-alias"),
        ],
    )
    def test_no_false_adr_0019(self, sample_config, tmp_path, source):
        """subaudit_A r8: these inputs are not stdlib logging."""
        assert [f for f in _adr(sample_config, tmp_path, source) if f["rule"] == "ADR-0019"] == []

    def test_import_logging_still_flagged_p0(self, sample_config, tmp_path):
        findings = _adr(sample_config, tmp_path, "import logging\n")
        assert [(f["rule"], f["severity"], f["line"]) for f in findings] == [("ADR-0019", "P0", 6)]

    @pytest.mark.parametrize(
        "source",
        [
            "from logging import getLogger\n",
            "import logging.handlers\n",
            "import logging as stdlog\n",
        ],
    )
    def test_other_stdlib_logging_imports_flagged(self, sample_config, tmp_path, source):
        findings = _adr(sample_config, tmp_path, source)
        assert any(f["rule"] == "ADR-0019" and f["severity"] == "P0" for f in findings)

    def test_naive_datetime_mentioned_in_string_not_flagged(self, sample_config, tmp_path):
        source = 'MSG = "never call datetime.now() bare"\n'
        assert [f for f in _adr(sample_config, tmp_path, source) if f["rule"] == "ADR-0083"] == []

    def test_aware_datetime_not_flagged_naive_flagged(self, sample_config, tmp_path):
        source = (
            "from datetime import datetime, timezone\n"
            "a = datetime.now(tz=timezone.utc)\n"
            "b = datetime.now(timezone.utc)\n"
            "c = datetime.now()  # timezone handled elsewhere\n"
        )
        findings = [f for f in _adr(sample_config, tmp_path, source) if f["rule"] == "ADR-0083"]
        assert [(f["line"], f["severity"]) for f in findings] == [(9, "P1")]

    def test_unparseable_file_is_reported(self, sample_config, tmp_path):
        findings = _adr(sample_config, tmp_path, "def broken(:\n")
        assert [f["rule"] for f in findings] == [ENGINE_ERROR_RULE]
        assert findings[0]["tool"] == "adr_checker"

    def test_engine_self_scan_is_clean(self, sample_config):
        engine_src = REPO_ROOT / "scripts" / "l11" / "deterministic_engine.py"
        assert DeterministicEngine(sample_config)._check_adr_compliance([str(engine_src)]) == []


# ─────────────────────────────────────────────
# OBS-07 regression: an enabled check with no implementation fails closed
# ─────────────────────────────────────────────
UNIMPLEMENTED_IN_SHIPPED = (
    "dependency_graph_validator",
    "schema_validator",
    "test_coverage_threshold",
    "secrets_scan",
)


class TestUnimplementedChecksFailClosed:
    async def test_enabled_unknown_engine_fails_with_engine_error(self, sample_config):
        cfg = _config_with(sample_config, "dependency_graph_validator")
        result = await DeterministicEngine(cfg).scan(["a.py"])
        assert result["passed"] is False
        errors = _engine_errors(result, "dependency_graph_validator")
        assert len(errors) == 1
        assert "dependency_graph_validator" in errors[0]["message"]

    async def test_enabled_unknown_layer_block_fails_with_engine_error(self, sample_config):
        cfg = _config_with(sample_config, secrets_scan={"enabled": True, "tool": "gitleaks"})
        result = await DeterministicEngine(cfg).scan(["a.py"])
        assert result["passed"] is False
        errors = _engine_errors(result, "secrets_scan")
        assert len(errors) == 1
        assert "secrets_scan" in errors[0]["message"]

    async def test_disabled_unknown_checks_are_ignored(self, sample_config):
        cfg = _config_with(sample_config, secrets_scan={"enabled": False})
        cfg["detection"]["deterministic_layer"]["engines"] = [
            {"name": "schema_validator", "enabled": False}
        ]
        result = await DeterministicEngine(cfg).scan(["a.py"])
        assert result == {"passed": True, "findings": []}

    @pytest.mark.parametrize("name", UNIMPLEMENTED_IN_SHIPPED)
    def test_shipped_config_disables_unimplemented_check(self, name):
        layer = yaml.safe_load(SHIPPED_CONFIG.read_text())["detection"]["deterministic_layer"]
        engines = {e["name"]: e for e in layer["engines"]}
        entry = engines.get(name, layer.get(name))
        assert entry is not None, name
        assert entry.get("enabled") is False

    def test_shipped_config_has_no_unimplemented_enabled_check(self):
        cfg = yaml.safe_load(SHIPPED_CONFIG.read_text())
        errors = DeterministicEngine(cfg)._unimplemented_check_errors()
        assert errors == []
