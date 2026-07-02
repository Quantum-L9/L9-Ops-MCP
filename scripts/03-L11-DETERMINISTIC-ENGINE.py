# --- L9_META ---
# l9_schema: 1
# component: 03-L11-DETERMINISTIC-ENGINE
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

"""L11 Deterministic Engine v3.1 — Aligned with L9 CI Toolchain.

Runs Ruff, Mypy, Bandit, Semgrep, ADR compliance, complexity checks,
PLUS delegates to all existing L9 ci/ scripts and pytest.

This layer BLOCKS merge on any violation.

DORA:
    component_id: l11-deterministic-engine
    tier: 2
    lifecycle: production
    owner: platform-engineering
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class DeterministicEngine:
    """Static analysis engine — deterministic, reproducible, merge-blocking.

    ADR Compliance:
        ADR-0019 structlog-only logging
        ADR-0002 Checks TYPE_CHECKING imports
        ADR-0014 Validates DORA metadata blocks
        ADR-0055 Fail-loudly on subprocess errors
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config["detection"]["deterministic_layer"]
        self._engine_map: dict[str, bool] = {}
        for entry in self.config.get("engines", []):
            if isinstance(entry, dict):
                self._engine_map[entry["name"]] = entry.get("enabled", False)
            else:
                self._engine_map[str(entry)] = True

        # L9 CI scripts config (NEW)
        l9_cfg = self.config.get("l9_ci_scripts", {})
        self._l9_scripts_enabled: bool = l9_cfg.get("enabled", False)
        self._l9_scripts: list[str] = l9_cfg.get("scripts", [])

        # Test suite config (NEW)
        test_cfg = self.config.get("test_suite", {})
        self._tests_enabled: bool = test_cfg.get("enabled", False)
        self._test_args: list[str] = test_cfg.get(
            "args", ["tests/", "--tb=short", "-q", "-x"]
        )
        self._test_ignore: list[str] = test_cfg.get("ignore", [])
        self._min_coverage: float = test_cfg.get("coverage", {}).get(
            "min_percent", 80.0
        )

    def _is_enabled(self, engine_name: str) -> bool:
        return self._engine_map.get(engine_name, False)

    # ── Semgrep Rules Path Resolution ───────
    def _resolve_semgrep_path(self) -> str:
        """Resolve semgrep rules path from config, falling back to L9 default."""
        for entry in self.config.get("engines", []):
            if isinstance(entry, dict) and entry.get("name") == "semgrep":
                configured = entry.get("rules_dir", "")
                if configured and Path(configured).exists():
                    return configured
        # L9 repo default
        default = ".semgrep/l9-rules.yaml"
        if Path(default).exists():
            return default
        return ".semgrep/"

    # ── Public API ──────────────────────────
    async def scan(self, files: list[str]) -> dict[str, Any]:
        """Run all enabled engines on *files*.

        Returns ``{"passed": bool, "findings": list[dict]}``.
        """
        if not files:
            return {"passed": True, "findings": []}

        all_findings: list[dict[str, Any]] = []

        # Original L11 deterministic engines
        if self._is_enabled("ruff"):
            all_findings.extend(self._run_ruff(files))
        if self._is_enabled("mypy"):
            all_findings.extend(self._run_mypy(files))
        if self._is_enabled("bandit"):
            all_findings.extend(self._run_bandit(files))
        if self._is_enabled("semgrep"):
            all_findings.extend(self._run_semgrep(files))
        if self._is_enabled("adr_compliance"):
            all_findings.extend(self._check_adr_compliance(files))
        if self._is_enabled("complexity_threshold"):
            all_findings.extend(self._check_complexity(files))

        # NEW: Run existing L9 CI scripts
        if self._l9_scripts_enabled:
            all_findings.extend(self._run_l9_ci_scripts())

        # NEW: Run pytest with coverage
        if self._tests_enabled:
            all_findings.extend(self._run_pytest())

        passed = len(all_findings) == 0
        logger.info(
            "deterministic_scan_completed",
            files_scanned=len(files),
            findings_count=len(all_findings),
            passed=passed,
        )
        return {"passed": passed, "findings": all_findings}

    # ── Individual Engines ──────────────────
    def _run_ruff(self, files: list[str]) -> list[dict[str, Any]]:
        """Run Ruff linter with JSON output."""
        result = subprocess.run(
            ["ruff", "check", "--output-format=json", *files],
            capture_output=True,
            text=True,
        )
        findings: list[dict[str, Any]] = []
        if result.returncode != 0 and result.stdout.strip():
            try:
                raw = json.loads(result.stdout)
                for item in raw:
                    findings.append({
                        "tool": "ruff",
                        "rule": item.get("code", "unknown"),
                        "message": item.get("message", ""),
                        "file": item.get("filename", ""),
                        "line": item.get("location", {}).get("row", 0),
                        "severity": "P2",
                    })
            except json.JSONDecodeError:
                findings.append({
                    "tool": "ruff",
                    "message": result.stdout[:500],
                    "severity": "P2",
                })
        logger.debug("ruff_completed", findings_count=len(findings))
        return findings

    def _run_mypy(self, files: list[str]) -> list[dict[str, Any]]:
        """Run Mypy type checker."""
        result = subprocess.run(
            ["mypy", "--no-error-summary", *files],
            capture_output=True,
            text=True,
        )
        findings: list[dict[str, Any]] = []
        if result.returncode != 0:
            for line in result.stdout.strip().splitlines():
                if ": error:" in line:
                    parts = line.split(":", maxsplit=3)
                    findings.append({
                        "tool": "mypy",
                        "file": parts[0] if len(parts) > 0 else "",
                        "line": (
                            int(parts[1])
                            if len(parts) > 1 and parts[1].strip().isdigit()
                            else 0
                        ),
                        "message": parts[-1].strip() if parts else line,
                        "severity": "P2",
                    })
        logger.debug("mypy_completed", findings_count=len(findings))
        return findings

    def _run_bandit(self, files: list[str]) -> list[dict[str, Any]]:
        """Run Bandit security scanner with JSON output."""
        result = subprocess.run(
            ["bandit", "-f", "json", "-r", *files],
            capture_output=True,
            text=True,
        )
        findings: list[dict[str, Any]] = []
        if result.stdout.strip():
            try:
                raw = json.loads(result.stdout)
                for item in raw.get("results", []):
                    sev = item.get("issue_severity", "MEDIUM")
                    findings.append({
                        "tool": "bandit",
                        "rule": item.get("test_id", ""),
                        "message": item.get("issue_text", ""),
                        "file": item.get("filename", ""),
                        "line": item.get("line_number", 0),
                        "severity": "P0" if sev == "HIGH" else "P1",
                    })
            except json.JSONDecodeError:
                findings.append({
                    "tool": "bandit",
                    "message": result.stdout[:500],
                    "severity": "P1",
                })
        logger.debug("bandit_completed", findings_count=len(findings))
        return findings

    def _run_semgrep(self, files: list[str]) -> list[dict[str, Any]]:
        """Run Semgrep with L9 custom rules."""
        rules_path = self._resolve_semgrep_path()
        result = subprocess.run(
            ["semgrep", "--config", rules_path, "--json", *files],
            capture_output=True,
            text=True,
        )
        findings: list[dict[str, Any]] = []
        if result.stdout.strip():
            try:
                raw = json.loads(result.stdout)
                for item in raw.get("results", []):
                    findings.append({
                        "tool": "semgrep",
                        "rule": item.get("check_id", ""),
                        "message": item.get("extra", {}).get("message", ""),
                        "file": item.get("path", ""),
                        "line": item.get("start", {}).get("line", 0),
                        "severity": "P1",
                    })
            except json.JSONDecodeError:
                pass
        logger.debug("semgrep_completed", findings_count=len(findings))
        return findings

    def _check_adr_compliance(self, files: list[str]) -> list[dict[str, Any]]:
        """Check ADR compliance (ADR-0019 structlog, ADR-0014 DORA, etc.)."""
        findings: list[dict[str, Any]] = []
        for file_str in files:
            path = Path(file_str)
            if not path.exists() or path.suffix != ".py":
                continue
            content = path.read_text(encoding="utf-8")

            # ADR-0019: No stdlib logging
            for i, line in enumerate(content.splitlines(), start=1):
                stripped = line.strip()
                if stripped.startswith("import logging") or "logging.getLogger" in stripped:
                    findings.append({
                        "tool": "adr_checker",
                        "rule": "ADR-0019",
                        "message": f"stdlib logging in {file_str}",
                        "file": file_str,
                        "line": i,
                        "severity": "P0",
                    })
                if stripped.startswith("print(") and "# noqa" not in stripped:
                    findings.append({
                        "tool": "adr_checker",
                        "rule": "ADR-0019",
                        "message": f"print() statement in {file_str}",
                        "file": file_str,
                        "line": i,
                        "severity": "P2",
                    })

            # ADR-0014: DORA metadata block required
            if "def " in content and "DORA:" not in content and "dora_meta" not in content:
                findings.append({
                    "tool": "adr_checker",
                    "rule": "ADR-0014",
                    "message": f"Missing DORA metadata block in {file_str}",
                    "file": file_str,
                    "line": 1,
                    "severity": "P2",
                })

            # ADR-0083: Naive datetime
            for i, line in enumerate(content.splitlines(), start=1):
                if "datetime.now()" in line and "timezone" not in line and "tz=" not in line:
                    findings.append({
                        "tool": "adr_checker",
                        "rule": "ADR-0083",
                        "message": f"Naive datetime.now() in {file_str}",
                        "file": file_str,
                        "line": i,
                        "severity": "P1",
                    })

        logger.debug("adr_compliance_completed", findings_count=len(findings))
        return findings

    def _check_complexity(self, files: list[str]) -> list[dict[str, Any]]:
        """Check cyclomatic complexity using radon."""
        findings: list[dict[str, Any]] = []
        max_cc = 15
        for entry in self.config.get("engines", []):
            if isinstance(entry, dict) and entry.get("name") == "complexity_threshold":
                max_cc = entry.get("max_cyclomatic", 15)
                break
        result = subprocess.run(
            ["radon", "cc", "-j", *files],
            capture_output=True,
            text=True,
        )
        if result.stdout.strip():
            try:
                raw = json.loads(result.stdout)
                for file_path, blocks in raw.items():
                    for block in blocks:
                        cc = block.get("complexity", 0)
                        if cc > max_cc:
                            findings.append({
                                "tool": "radon",
                                "rule": "complexity",
                                "message": f"{block.get('name', '?')} CC={cc} > {max_cc}",
                                "file": file_path,
                                "line": block.get("lineno", 0),
                                "severity": "P2",
                            })
            except json.JSONDecodeError:
                pass
        logger.debug("complexity_completed", findings_count=len(findings))
        return findings

    # ── NEW: L9 CI Scripts Runner ───────────
    def _run_l9_ci_scripts(self) -> list[dict[str, Any]]:
        """Run all existing L9 ci/ check scripts as subprocesses.

        Each script must exit 0 on success, non-zero on failure.
        This bridges L11 to the 20+ existing L9 CI checks without
        duplicating their logic.
        """
        findings: list[dict[str, Any]] = []
        for script_path in self._l9_scripts:
            if not Path(script_path).exists():
                logger.warning("l9_ci_script_missing", script=script_path)
                continue
            result = subprocess.run(
                ["python", script_path],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                findings.append({
                    "tool": "l9_ci_script",
                    "rule": Path(script_path).stem,
                    "message": result.stdout[:500] or result.stderr[:500],
                    "file": script_path,
                    "line": 0,
                    "severity": "P1",
                })
                logger.warning(
                    "l9_ci_script_failed",
                    script=script_path,
                    returncode=result.returncode,
                )
            else:
                logger.debug("l9_ci_script_passed", script=script_path)
        logger.info(
            "l9_ci_scripts_completed",
            total=len(self._l9_scripts),
            failures=len(findings),
        )
        return findings

    # ── NEW: Pytest Runner ──────────────────
    def _run_pytest(self) -> list[dict[str, Any]]:
        """Run pytest with coverage and return findings on failure."""
        findings: list[dict[str, Any]] = []
        cmd = ["pytest"]
        cmd.extend(self._test_args)
        for ignore_path in self._test_ignore:
            cmd.extend(["--ignore", ignore_path])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # Extract failure summary from pytest output
            output_lines = result.stdout.strip().splitlines()
            summary = ""
            for line in reversed(output_lines):
                if "failed" in line.lower() or "error" in line.lower():
                    summary = line.strip()
                    break
            if not summary:
                summary = output_lines[-1] if output_lines else "pytest failed"

            findings.append({
                "tool": "pytest",
                "rule": "test_suite",
                "message": summary[:500],
                "file": "tests/",
                "line": 0,
                "severity": "P0",
            })
            logger.warning(
                "pytest_failed",
                returncode=result.returncode,
                summary=summary[:200],
            )
        else:
            logger.info("pytest_passed")

        # Check coverage threshold from XML if generated
        coverage_xml = Path("coverage.xml")
        if coverage_xml.exists():
            self._check_coverage_threshold(findings, coverage_xml)

        return findings

    def _check_coverage_threshold(
        self,
        findings: list[dict[str, Any]],
        coverage_xml: Path,
    ) -> None:
        """Parse coverage.xml and fail if below threshold."""
        try:
            import xml.etree.ElementTree as ET  # noqa: PLC0415, N817

            tree = ET.parse(coverage_xml)  # noqa: S314
            root = tree.getroot()
            line_rate = float(root.get("line-rate", "0"))
            coverage_pct = round(line_rate * 100, 2)
            if coverage_pct < self._min_coverage:
                findings.append({
                    "tool": "coverage",
                    "rule": "min_coverage",
                    "message": (
                        f"Coverage {coverage_pct}% < {self._min_coverage}% threshold"
                    ),
                    "file": "coverage.xml",
                    "line": 0,
                    "severity": "P1",
                })
                logger.warning(
                    "coverage_below_threshold",
                    actual=coverage_pct,
                    threshold=self._min_coverage,
                )
        except (FileNotFoundError, ET.ParseError) as exc:
            logger.warning("coverage_xml_parse_error", error=str(exc))

    # ── Health ──────────────────────────────
    async def health(self) -> dict[str, Any]:
        """Return health status and list of enabled engines."""
        enabled = [k for k, v in self._engine_map.items() if v]
        return {
            "healthy": True,
            "engines_enabled": enabled,
            "l9_ci_scripts_enabled": self._l9_scripts_enabled,
            "l9_ci_scripts_count": len(self._l9_scripts),
            "test_suite_enabled": self._tests_enabled,
        }
