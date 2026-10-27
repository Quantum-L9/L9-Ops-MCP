# --- L9_META ---
# l9_schema: 1
# component: orchestrator
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

"""L11 Debt Governance Orchestrator v3.0.

Two-layer orchestration: deterministic (blocking) + AI (async enrichment).

DORA:
    component_id: l11-debt-orchestrator
    tier: 2
    lifecycle: production
    owner: platform-engineering
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar

import structlog

logger = structlog.get_logger(__name__)


# ─────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────
@dataclass
class Finding:
    """Single debt finding from any detection engine.

    The canonical wire shape is the producer contract of
    ``DeterministicEngine.scan`` (``scripts/l11/deterministic_engine.py``):
    a mapping with ``tool``, ``rule``, ``message``, ``file``, ``line`` and
    ``severity``.  ``RiskScorer`` and ``DebtGraphService`` read those same keys,
    so :meth:`to_dict` must emit them unchanged.
    """

    REQUIRED_KEYS: ClassVar[tuple[str, ...]] = ("tool", "message", "severity")

    tool: str
    message: str
    severity: str
    rule: str = ""
    file: str = ""
    line: int = 0
    risk_score: float = 0.0
    owner: str | None = None
    finding_hash: str = ""
    ai_enrichment: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> Finding:
        """Build a Finding from a producer dict.

        Raises:
            ValueError: If *raw* is not a mapping or lacks a required key.
        """
        if not isinstance(raw, Mapping):
            msg = f"producer finding must be a mapping, got {type(raw).__name__}"
            raise ValueError(msg)
        missing = [k for k in cls.REQUIRED_KEYS if not isinstance(raw.get(k), str)]
        if missing:
            msg = f"producer finding missing required string keys: {', '.join(missing)}"
            raise ValueError(msg)
        line = raw.get("line", 0)
        enrichment = raw.get("ai_enrichment")
        return cls(
            tool=raw["tool"],
            message=raw["message"],
            severity=raw["severity"],
            rule=str(raw.get("rule") or ""),
            file=str(raw.get("file") or ""),
            line=line if isinstance(line, int) else 0,
            owner=raw.get("owner"),
            ai_enrichment=dict(enrichment) if isinstance(enrichment, Mapping) else {},
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize finding for scoring and JSON/Neo4j storage (producer keys)."""
        return {
            "tool": self.tool,
            "rule": self.rule,
            "message": self.message,
            "severity": self.severity,
            "file": self.file,
            "line": self.line,
            "risk_score": self.risk_score,
            "owner": self.owner,
            "finding_hash": self.finding_hash,
            "ai_enrichment": self.ai_enrichment,
            "created_at": self.created_at.isoformat(),
        }


def findings_from_producer(raw_findings: Any) -> list[Finding]:
    """Convert producer output into Findings.

    A malformed entry does not abort the scan: it becomes a failing
    ``malformed_finding`` Finding so the scan cannot pass on bad input.
    """
    if not isinstance(raw_findings, list):
        logger.error("malformed_producer_findings", type=type(raw_findings).__name__)
        return [
            Finding(
                tool="l11_orchestrator",
                rule="malformed_finding",
                message=(f"producer findings must be a list, got {type(raw_findings).__name__}"),
                severity="P1",
            )
        ]
    findings: list[Finding] = []
    for index, raw in enumerate(raw_findings):
        try:
            findings.append(Finding.from_dict(raw))
        except ValueError as exc:
            logger.error("malformed_producer_finding", index=index, error=str(exc))
            findings.append(
                Finding(
                    tool="l11_orchestrator",
                    rule="malformed_finding",
                    message=f"finding #{index} rejected: {exc}",
                    severity="P1",
                )
            )
    return findings


@dataclass
class ScanResult:
    """Aggregated result from a pipeline run."""

    passed: bool
    findings: list[Finding]
    should_block_merge: bool = False
    enrichment_queued: bool = False
    regressions: list[dict[str, Any]] = field(default_factory=list)
    duration_ms: float = 0.0


# ─────────────────────────────────────────────
# Config Loader
# ─────────────────────────────────────────────
def load_config(config_path: Path) -> dict[str, Any]:
    """Load pipeline YAML configuration.

    Args:
        config_path: Path to 01-L11-PIPELINE-CONFIG.yaml

    Returns:
        Parsed configuration dictionary.

    Raises:
        FileNotFoundError: If config file does not exist.
        ValueError: If YAML is malformed.
    """
    import yaml  # noqa: PLC0415

    if not config_path.exists():
        msg = f"Config not found: {config_path}"
        raise FileNotFoundError(msg)

    with open(config_path) as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict):
        msg = f"Config must be a YAML mapping, got {type(data).__name__}"
        raise ValueError(msg)

    logger.info("config_loaded", path=str(config_path))
    return data


# ─────────────────────────────────────────────
# Engine factories (imported lazily: engines never import the orchestrator)
# ─────────────────────────────────────────────
def _build_deterministic_engine(config: dict[str, Any]) -> Any:
    from scripts.l11.deterministic_engine import DeterministicEngine  # noqa: PLC0415

    return DeterministicEngine(config)


def _build_risk_scorer(config: dict[str, Any]) -> Any:
    from scripts.l11.risk_scorer import RiskScorer  # noqa: PLC0415

    return RiskScorer(config)


def _build_debt_graph(config: dict[str, Any]) -> Any:
    from scripts.l11.debt_graph_service import DebtGraphService  # noqa: PLC0415

    return DebtGraphService(config)


def _build_ai_engine(config: dict[str, Any]) -> Any:
    from scripts.l11.ai_enrichment_engine import AIEnrichmentEngine  # noqa: PLC0415

    return AIEnrichmentEngine(config)


# ─────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────
class L11Orchestrator:
    """Two-layer debt governance orchestrator.

    Deterministic layer blocks merges.  AI layer enriches asynchronously.

    ADR Compliance:
        ADR-0019  structlog-only logging
        ADR-0055  Fail-loudly on critical errors
        ADR-0083  UTC datetime standard
    """

    #: Components without which a scan cannot produce a merge decision.
    REQUIRED_COMPONENTS: ClassVar[tuple[str, ...]] = ("deterministic_engine", "risk_scorer")

    def __init__(
        self,
        config_path: Path,
        *,
        deterministic_engine: Any | None = None,
        ai_engine: Any | None = None,
        debt_graph: Any | None = None,
        risk_scorer: Any | None = None,
    ) -> None:
        """Load config and build every engine not injected (ADR-0052 DI/DIP).

        Required engines (deterministic engine, risk scorer) are built from
        config; optional ones (debt graph, AI engine) are built when their
        config section is present.

        Raises:
            ValueError: If a required engine cannot be built from config.
        """
        self.config = load_config(config_path)
        self.deterministic_engine = deterministic_engine
        if self.deterministic_engine is None:
            self.deterministic_engine = self._build(
                "deterministic_engine", _build_deterministic_engine
            )
        self.risk_scorer = risk_scorer
        if self.risk_scorer is None:
            self.risk_scorer = self._build("risk_scorer", _build_risk_scorer)
        self.debt_graph = debt_graph
        if self.debt_graph is None and "state_management" in self.config:
            self.debt_graph = self._build("debt_graph", _build_debt_graph)
        self.ai_engine = ai_engine
        if self.ai_engine is None and "ai_layer" in self.config.get("detection", {}):
            self.ai_engine = self._build("ai_engine", _build_ai_engine)

    def _build(self, name: str, factory: Any) -> Any:
        try:
            return factory(self.config)
        except (KeyError, TypeError, AttributeError) as exc:
            msg = f"cannot build {name} from config: missing or invalid {exc}"
            raise ValueError(msg) from exc

    # ── PR Scan (Incremental) ───────────────
    async def run_pr_scan(
        self,
        pr_number: int,
        changed_files: list[str],
    ) -> ScanResult:
        """Run incremental PR scan.

        Phase 1 — Deterministic (BLOCKING).
        Phase 2 — Risk scoring.
        Phase 3 — Debt graph upsert.
        Phase 4 — Merge decision.
        Phase 5 — Queue AI enrichment (NON-BLOCKING).
        """
        start = datetime.now(tz=timezone.utc)
        logger.info(
            "pr_scan_started",
            pr_number=pr_number,
            file_count=len(changed_files),
        )

        # Phase 1
        det_result = await self.deterministic_engine.scan(changed_files)
        findings = findings_from_producer(det_result.get("findings"))
        passed = bool(det_result.get("passed")) and not findings

        # Phase 2
        for f in findings:
            f.risk_score = self.risk_scorer.calculate(f.to_dict())

        # Phase 3
        if self.debt_graph is not None:
            await self.debt_graph.upsert_findings([f.to_dict() for f in findings])

        # Phase 4
        block_threshold: int = self.config["risk_model"]["thresholds"]["block_pr"]
        should_block = any(f.risk_score >= block_threshold for f in findings)

        # Phase 5
        enrichment_queued = False
        pr_cfg = self.config["execution"]["triggers"]["pr"]
        if pr_cfg.get("ai_enrichment_async") and self.ai_engine is not None:
            asyncio.create_task(self.ai_engine.enqueue_enrichment([f.to_dict() for f in findings]))
            enrichment_queued = True

        duration_ms = (datetime.now(tz=timezone.utc) - start).total_seconds() * 1000.0

        logger.info(
            "pr_scan_completed",
            pr_number=pr_number,
            findings_count=len(findings),
            should_block=should_block,
            enrichment_queued=enrichment_queued,
            duration_ms=round(duration_ms, 1),
        )

        return ScanResult(
            passed=passed,
            findings=findings,
            should_block_merge=should_block,
            enrichment_queued=enrichment_queued,
            duration_ms=duration_ms,
        )

    # ── Nightly Full-Repo Scan ──────────────
    async def run_nightly_scan(
        self,
        scope: list[str],
    ) -> ScanResult:
        """Run full-repo nightly scan with AI enrichment.

        Phase 1 — Deterministic scan.
        Phase 2 — Risk scoring.
        Phase 3 — Debt graph upsert.
        Phase 4 — AI enrichment (blocking for nightly).
        Phase 5 — Regression detection.
        """
        start = datetime.now(tz=timezone.utc)
        logger.info("nightly_scan_started", scope=scope)

        det_result = await self.deterministic_engine.scan(scope)
        findings = findings_from_producer(det_result.get("findings"))
        passed = bool(det_result.get("passed")) and not findings

        for f in findings:
            f.risk_score = self.risk_scorer.calculate(f.to_dict())

        if self.debt_graph is not None:
            await self.debt_graph.upsert_findings([f.to_dict() for f in findings])

        sched_cfg = self.config["execution"]["triggers"]["schedule"]
        if sched_cfg.get("ai_enrichment") and self.ai_engine is not None:
            enriched = await self.ai_engine.enrich_batch([f.to_dict() for f in findings])
            for f, e in zip(findings, enriched, strict=True):
                f.ai_enrichment = e.get("ai_enrichment", {})

        regressions: list[dict[str, Any]] = []
        if self.debt_graph is not None:
            regressions = await self.debt_graph.detect_regressions()

        duration_ms = (datetime.now(tz=timezone.utc) - start).total_seconds() * 1000.0

        logger.info(
            "nightly_scan_completed",
            findings_count=len(findings),
            regressions_count=len(regressions),
            duration_ms=round(duration_ms, 1),
        )

        return ScanResult(
            passed=passed,
            findings=findings,
            regressions=regressions,
            duration_ms=duration_ms,
        )

    # ── Health Check ────────────────────────
    async def health_check(self) -> dict[str, Any]:
        """Health check for all pipeline components."""
        components: dict[str, Any] = {}

        if self.deterministic_engine is not None:
            components["deterministic_engine"] = await self.deterministic_engine.health()
        if self.ai_engine is not None:
            components["ai_engine"] = await self.ai_engine.health()
        if self.debt_graph is not None:
            components["debt_graph"] = await self.debt_graph.health()
        if self.risk_scorer is not None:
            components["risk_scorer"] = self.risk_scorer.health()

        missing = [name for name in self.REQUIRED_COMPONENTS if getattr(self, name) is None]
        all_healthy = not missing and all(v.get("healthy", False) for v in components.values())
        return {
            "healthy": all_healthy,
            "components": components,
            "missing_components": missing,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }
