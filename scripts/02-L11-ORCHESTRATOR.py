# --- L9_META ---
# l9_schema: 1
# component: 02-L11-ORCHESTRATOR
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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ─────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────
@dataclass
class Finding:
    """Single debt finding from any detection engine."""

    tool: str
    message: str
    severity: str
    file_path: str = ""
    line: int = 0
    risk_score: float = 0.0
    owner: str | None = None
    finding_hash: str = ""
    ai_enrichment: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Serialize finding for JSON/Neo4j storage."""
        return {
            "tool": self.tool,
            "message": self.message,
            "severity": self.severity,
            "file_path": self.file_path,
            "line": self.line,
            "risk_score": self.risk_score,
            "owner": self.owner,
            "finding_hash": self.finding_hash,
            "ai_enrichment": self.ai_enrichment,
            "created_at": self.created_at.isoformat(),
        }


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

    def __init__(
        self,
        config_path: Path,
        *,
        deterministic_engine: Any | None = None,
        ai_engine: Any | None = None,
        debt_graph: Any | None = None,
        risk_scorer: Any | None = None,
    ) -> None:
        self.config = load_config(config_path)
        # Accept injected engines for testability (ADR-0052 DI/DIP).
        self.deterministic_engine = deterministic_engine
        self.ai_engine = ai_engine
        self.debt_graph = debt_graph
        self.risk_scorer = risk_scorer

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
        findings: list[Finding] = det_result["findings"]

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
            passed=det_result["passed"],
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
        findings: list[Finding] = det_result["findings"]

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
            passed=det_result["passed"],
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

        all_healthy = all(v.get("healthy", False) for v in components.values())
        return {
            "healthy": all_healthy,
            "components": components,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }
