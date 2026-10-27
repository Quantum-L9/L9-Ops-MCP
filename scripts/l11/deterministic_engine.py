# --- L9_META ---
# l9_schema: 1
# component: deterministic_engine
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

#: Rule of a finding that reports a configured check which could not run
#: (missing binary/script, abnormal exit, unparseable output, timeout, crash).
#: Such a finding fails the scan: the blocking layer never passes on a check
#: it did not complete.
ENGINE_ERROR_RULE = "engine_error"


def engine_error(tool: str, message: str, file: str = "") -> dict[str, Any]:
    """Build a failing finding (producer contract keys) for an unrunnable check."""
    return {
        "tool": tool,
        "rule": ENGINE_ERROR_RULE,
        "message": message[:500],
        "file": file,
        "line": 0,
        "severity": "P1",
    }


def _describe(result: subprocess.CompletedProcess[str]) -> str:
    detail = (result.stderr or result.stdout or "").strip()
    return f"exit {result.returncode}: {detail[:400]}" if detail else f"exit {result.returncode}"


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

        # Per-tool subprocess timeout; None (default) means no timeout.
        self._tool_timeout: float | None = self.config.get("tool_timeout_seconds")

        # L9 CI scripts config (NEW)
        l9_cfg = self.config.get("l9_ci_scripts", {})
        self._l9_scripts_enabled: bool = l9_cfg.get("enabled", False)
        self._l9_scripts: list[str] = l9_cfg.get("scripts", [])

        # Test suite config (NEW)
        test_cfg = self.config.get("test_suite", {})
        self._tests_enabled: bool = test_cfg.get("enabled", False)
        self._test_args: list[str] = test_cfg.get("args", ["tests/", "--tb=short", "-q", "-x"])
        self._test_ignore: list[str] = test_cfg.get("ignore", [])
        self._min_coverage: float = test_cfg.get("coverage", {}).get("min_percent", 80.0)

    def _is_enabled(self, engine_name: str) -> bool:
        return self._engine_map.get(engine_name, False)

    def _run(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603 — fixed tool argv, no shell
            cmd,
            capture_output=True,
            text=True,
            timeout=self._tool_timeout,
        )

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

        Returns ``{"passed": bool, "findings": list[dict]}``; ``passed`` is
        True only when no engine reported a finding.  An engine that raises
        or cannot run contributes an ``engine_error`` finding instead of
        aborting the scan.
        """
        if not files:
            return {"passed": True, "findings": []}

        all_findings: list[dict[str, Any]] = []
        engines: list[tuple[str, str, Any]] = [
            ("ruff", "ruff", lambda: self._run_ruff(files)),
            ("mypy", "mypy", lambda: self._run_mypy(files)),
            ("bandit", "bandit", lambda: self._run_bandit(files)),
            ("semgrep", "semgrep", lambda: self._run_semgrep(files)),
            ("adr_compliance", "adr_checker", lambda: self._check_adr_compliance(files)),
            ("complexity_threshold", "radon", lambda: self._check_complexity(files)),
        ]
        for name, tool, runner in engines:
            if self._is_enabled(name):
                all_findings.extend(self._isolated(tool, runner))

        # NEW: Run existing L9 CI scripts
        if self._l9_scripts_enabled:
            all_findings.extend(self._isolated("l9_ci_script", self._run_l9_ci_scripts))

        # NEW: Run pytest with coverage
        if self._tests_enabled:
            all_findings.extend(self._isolated("pytest", self._run_pytest))

        passed = len(all_findings) == 0
        logger.info(
            "deterministic_scan_completed",
            files_scanned=len(files),
            findings_count=len(all_findings),
            passed=passed,
        )
        return {"passed": passed, "findings": all_findings}

    @staticmethod
    def _isolated(tool: str, runner: Any) -> list[dict[str, Any]]:
        """Run one engine; any exception becomes a failing engine_error finding."""
        try:
            return list(runner())
        except Exception as exc:  # noqa: BLE001 — isolate engines; fail closed
            logger.error("deterministic_engine_failed", tool=tool, error=repr(exc))
            return [engine_error(tool, f"{type(exc).__name__}: {exc}")]

    # ── Individual Engines ──────────────────
    def _run_ruff(self, files: list[str]) -> list[dict[str, Any]]:
        """Run Ruff linter with JSON output (exit 0 clean, 1 violations)."""
        result = self._run(["ruff", "check", "--output-format=json", *files])
        if result.returncode not in (0, 1):
            return [engine_error("ruff", _describe(result))]
        findings: list[dict[str, Any]] = []
        if result.returncode == 1:
            try:
                raw = json.loads(result.stdout)
            except json.JSONDecodeError:
                return [engine_error("ruff", f"unparseable output: {_describe(result)}")]
            for item in raw:
                findings.append(
                    {
                        "tool": "ruff",
                        "rule": item.get("code", "unknown"),
                        "message": item.get("message", ""),
                        "file": item.get("filename", ""),
                        "line": item.get("location", {}).get("row", 0),
                        "severity": "P2",
                    }
                )
            if not findings:
                return [engine_error("ruff", f"exit 1 without violations: {_describe(result)}")]
        logger.debug("ruff_completed", findings_count=len(findings))
        return findings

    def _run_mypy(self, files: list[str]) -> list[dict[str, Any]]:
        """Run Mypy type checker (exit 0 clean, 1 type errors, 2 fatal)."""
        result = self._run(["mypy", "--no-error-summary", *files])
        if result.returncode not in (0, 1):
            return [engine_error("mypy", _describe(result))]
        findings: list[dict[str, Any]] = []
        if result.returncode == 1:
            for line in result.stdout.strip().splitlines():
                if ": error:" in line:
                    parts = line.split(":", maxsplit=3)
                    findings.append(
                        {
                            "tool": "mypy",
                            "file": parts[0] if len(parts) > 0 else "",
                            "line": (
                                int(parts[1])
                                if len(parts) > 1 and parts[1].strip().isdigit()
                                else 0
                            ),
                            "message": parts[-1].strip() if parts else line,
                            "severity": "P2",
                        }
                    )
            if not findings:
                return [engine_error("mypy", f"exit 1 without errors: {_describe(result)}")]
        logger.debug("mypy_completed", findings_count=len(findings))
        return findings

    def _run_bandit(self, files: list[str]) -> list[dict[str, Any]]:
        """Run Bandit security scanner with JSON output (exit 0 clean, 1 issues)."""
        result = self._run(["bandit", "-f", "json", "-r", *files])
        if result.returncode not in (0, 1):
            return [engine_error("bandit", _describe(result))]
        try:
            raw = json.loads(result.stdout)
        except json.JSONDecodeError:
            return [engine_error("bandit", f"unparseable output: {_describe(result)}")]
        findings: list[dict[str, Any]] = []
        for item in raw.get("results", []):
            sev = item.get("issue_severity", "MEDIUM")
            findings.append(
                {
                    "tool": "bandit",
                    "rule": item.get("test_id", ""),
                    "message": item.get("issue_text", ""),
                    "file": item.get("filename", ""),
                    "line": item.get("line_number", 0),
                    "severity": "P0" if sev == "HIGH" else "P1",
                }
            )
        if result.returncode == 1 and not findings:
            return [engine_error("bandit", f"exit 1 without issues: {_describe(result)}")]
        logger.debug("bandit_completed", findings_count=len(findings))
        return findings

    def _run_semgrep(self, files: list[str]) -> list[dict[str, Any]]:
        """Run Semgrep with L9 custom rules (exit 0/1 ran, >= 2 error)."""
        rules_path = self._resolve_semgrep_path()
        result = self._run(["semgrep", "--config", rules_path, "--json", *files])
        if result.returncode not in (0, 1):
            return [engine_error("semgrep", _describe(result))]
        try:
            raw = json.loads(result.stdout)
        except json.JSONDecodeError:
            return [engine_error("semgrep", f"unparseable output: {_describe(result)}")]
        findings: list[dict[str, Any]] = []
        for item in raw.get("results", []):
            findings.append(
                {
                    "tool": "semgrep",
                    "rule": item.get("check_id", ""),
                    "message": item.get("extra", {}).get("message", ""),
                    "file": item.get("path", ""),
                    "line": item.get("start", {}).get("line", 0),
                    "severity": "P1",
                }
            )
        logger.debug("semgrep_completed", findings_count=len(findings))
        return findings

    @staticmethod
    def _expand_python_files(files: list[str]) -> list[str]:
        """Expand directory scope entries to the ``.py`` files beneath them."""
        expanded: list[str] = []
        for file_str in files:
            path = Path(file_str)
            if path.is_dir():
                expanded.extend(str(p) for p in sorted(path.rglob("*.py")) if p.is_file())
            else:
                expanded.append(file_str)
        return expanded

    def _check_adr_compliance(self, files: list[str]) -> list[dict[str, Any]]:
        """Check ADR compliance (ADR-0019 structlog, ADR-0014 DORA, etc.)."""
        findings: list[dict[str, Any]] = []
        for file_str in self._expand_python_files(files):
            path = Path(file_str)
            if not path.exists() or path.suffix != ".py":
                continue
            content = path.read_text(encoding="utf-8")

            # ADR-0019: No stdlib logging
            for i, line in enumerate(content.splitlines(), start=1):
                stripped = line.strip()
                if stripped.startswith("import logging") or "logging.getLogger" in stripped:
                    findings.append(
                        {
                            "tool": "adr_checker",
                            "rule": "ADR-0019",
                            "message": f"stdlib logging in {file_str}",
                            "file": file_str,
                            "line": i,
                            "severity": "P0",
                        }
                    )
                if stripped.startswith("print(") and "# noqa" not in stripped:
                    findings.append(
                        {
                            "tool": "adr_checker",
                            "rule": "ADR-0019",
                            "message": f"print() statement in {file_str}",
                            "file": file_str,
                            "line": i,
                            "severity": "P2",
                        }
                    )

            # ADR-0014: DORA metadata block required
            if "def " in content and "DORA:" not in content and "dora_meta" not in content:
                findings.append(
                    {
                        "tool": "adr_checker",
                        "rule": "ADR-0014",
                        "message": f"Missing DORA metadata block in {file_str}",
                        "file": file_str,
                        "line": 1,
                        "severity": "P2",
                    }
                )

            # ADR-0083: Naive datetime
            for i, line in enumerate(content.splitlines(), start=1):
                if "datetime.now()" in line and "timezone" not in line and "tz=" not in line:
                    findings.append(
                        {
                            "tool": "adr_checker",
                            "rule": "ADR-0083",
                            "message": f"Naive datetime.now() in {file_str}",
                            "file": file_str,
                            "line": i,
                            "severity": "P1",
                        }
                    )

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
        result = self._run(["radon", "cc", "-j", *files])
        if result.returncode != 0:
            return [engine_error("radon", _describe(result))]
        try:
            raw = json.loads(result.stdout)
        except json.JSONDecodeError:
            return [engine_error("radon", f"unparseable output: {_describe(result)}")]
        for file_path, blocks in raw.items():
            if not isinstance(blocks, list):
                # radon reports a file it could not analyse as {"error": "..."}
                detail = blocks.get("error", blocks) if isinstance(blocks, dict) else blocks
                findings.append(engine_error("radon", f"cannot analyse: {detail}", file_path))
                continue
            for block in blocks:
                cc = block.get("complexity", 0)
                if cc > max_cc:
                    findings.append(
                        {
                            "tool": "radon",
                            "rule": "complexity",
                            "message": f"{block.get('name', '?')} CC={cc} > {max_cc}",
                            "file": file_path,
                            "line": block.get("lineno", 0),
                            "severity": "P2",
                        }
                    )
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
                # Configured but unrunnable: fail closed (D-07).
                logger.error("l9_ci_script_missing", script=script_path)
                findings.append(
                    engine_error(
                        "l9_ci_script", f"configured script missing: {script_path}", script_path
                    )
                )
                continue
            result = self._run(["python", script_path])
            if result.returncode != 0:
                findings.append(
                    {
                        "tool": "l9_ci_script",
                        "rule": Path(script_path).stem,
                        "message": result.stdout[:500] or result.stderr[:500],
                        "file": script_path,
                        "line": 0,
                        "severity": "P1",
                    }
                )
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

        result = self._run(cmd)
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

            findings.append(
                {
                    "tool": "pytest",
                    "rule": "test_suite",
                    "message": summary[:500],
                    "file": "tests/",
                    "line": 0,
                    "severity": "P0",
                }
            )
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
                findings.append(
                    {
                        "tool": "coverage",
                        "rule": "min_coverage",
                        "message": (f"Coverage {coverage_pct}% < {self._min_coverage}% threshold"),
                        "file": "coverage.xml",
                        "line": 0,
                        "severity": "P1",
                    }
                )
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
