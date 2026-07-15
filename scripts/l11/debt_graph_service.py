# --- L9_META ---
# l9_schema: 1
# component: debt_graph_service
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

"""L11 Debt Graph Service (Neo4j Backend).

Persistent debt tracking with deduplication, regression detection,
and aging-based priority escalation.

DORA:
    component_id: l11-debt-graph-service
    tier: 2
    lifecycle: production
    owner: platform-engineering
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class DebtGraphService:
    """Neo4j-backed persistent debt tracking with JSON fallback.

    ADR Compliance:
        ADR-0019  structlog-only logging
        ADR-0032  Neo4j Cypher query pattern
        ADR-0082  Neo4j required, not optional
        ADR-0083  UTC datetime standard
    """

    def __init__(self, config: dict[str, Any]) -> None:
        graph_cfg = config["state_management"]["debt_graph"]
        self._backend = graph_cfg.get("backend", "neo4j")
        self._driver: Any | None = None

        if self._backend == "neo4j":
            try:
                from neo4j import AsyncGraphDatabase  # noqa: PLC0415

                uri = os.getenv(graph_cfg.get("uri_env", "NEO4J_URI"), "")
                user = os.getenv(graph_cfg.get("user_env", "NEO4J_USER"), "")
                pw = os.getenv(graph_cfg.get("password_env", "NEO4J_PASSWORD"), "")
                if uri and user:
                    self._driver = AsyncGraphDatabase.driver(uri, auth=(user, pw))
                    logger.info("neo4j_connected", uri=uri)
                else:
                    logger.warning("neo4j_env_missing")
            except ImportError:
                logger.warning("neo4j_driver_not_installed")

        # JSON fallback config
        fb_cfg = config["state_management"].get("json_fallback", {})
        self._json_path = Path(fb_cfg.get("path", ".l11/debt_findings.json"))

        aging_cfg = config["risk_model"].get("aging_policy", {})
        self._p2_to_p1_days: int = aging_cfg.get("p2_to_p1_days", 30)
        self._p1_to_p0_days: int = aging_cfg.get("p1_to_p0_days", 60)

    # ── Public API ──────────────────────────
    async def upsert_findings(self, findings: list[dict[str, Any]]) -> int:
        """Upsert findings with deduplication by content hash.

        Returns count of upserted findings.
        """
        now = datetime.now(tz=timezone.utc).isoformat()
        upserted = 0

        if self._driver is not None:
            async with self._driver.session() as session:
                for finding in findings:
                    fhash = self._compute_hash(finding)
                    await session.run(
                        """
                        MERGE (f:Finding {hash: $hash})
                        ON CREATE SET
                            f.first_seen = datetime($now),
                            f.last_seen  = datetime($now),
                            f.tool       = $tool,
                            f.rule       = $rule,
                            f.message    = $message,
                            f.severity   = $severity,
                            f.file       = $file,
                            f.line       = $line,
                            f.risk_score = $risk_score,
                            f.status     = 'open'
                        ON MATCH SET
                            f.last_seen  = datetime($now),
                            f.risk_score = $risk_score,
                            f.status     = CASE
                                WHEN f.status = 'fixed' THEN 'regressed'
                                ELSE f.status
                            END
                        """,
                        {
                            "hash": fhash,
                            "now": now,
                            "tool": finding.get("tool", ""),
                            "rule": finding.get("rule", ""),
                            "message": finding.get("message", ""),
                            "severity": finding.get("severity", "P3"),
                            "file": finding.get("file", ""),
                            "line": finding.get("line", 0),
                            "risk_score": finding.get("risk_score", 0.0),
                        },
                    )
                    upserted += 1
        else:
            # JSON fallback
            upserted = self._upsert_json(findings, now)

        logger.info("findings_upserted", count=upserted)
        return upserted

    async def detect_regressions(self) -> list[dict[str, Any]]:
        """Detect findings that were fixed but reappeared."""
        regressions: list[dict[str, Any]] = []

        if self._driver is not None:
            async with self._driver.session() as session:
                result = await session.run(
                    """
                    MATCH (f:Finding)
                    WHERE f.status = 'regressed'
                    RETURN f.hash AS hash,
                           f.message AS message,
                           f.file AS file,
                           f.severity AS severity,
                           f.first_seen AS first_seen
                    ORDER BY f.first_seen DESC
                    LIMIT 100
                    """
                )
                regressions = [dict(r) async for r in result]
        else:
            regressions = self._detect_regressions_json()

        logger.info("regressions_detected", count=len(regressions))
        return regressions

    async def apply_aging_policy(self) -> int:
        """Escalate priorities based on age thresholds.

        P2 open > p2_to_p1_days  →  P1
        P1 open > p1_to_p0_days  →  P0
        """
        escalated = 0
        if self._driver is not None:
            async with self._driver.session() as session:
                # P2 → P1
                r1 = await session.run(
                    """
                    MATCH (f:Finding)
                    WHERE f.severity = 'P2'
                      AND f.status = 'open'
                      AND f.first_seen < datetime() - duration({days: $days})
                    SET f.severity = 'P1'
                    RETURN count(f) AS cnt
                    """,
                    {"days": self._p2_to_p1_days},
                )
                rec = await r1.single()
                escalated += rec["cnt"] if rec else 0

                # P1 → P0
                r2 = await session.run(
                    """
                    MATCH (f:Finding)
                    WHERE f.severity = 'P1'
                      AND f.status = 'open'
                      AND f.first_seen < datetime() - duration({days: $days})
                    SET f.severity = 'P0'
                    RETURN count(f) AS cnt
                    """,
                    {"days": self._p1_to_p0_days},
                )
                rec2 = await r2.single()
                escalated += rec2["cnt"] if rec2 else 0

        logger.info("aging_policy_applied", escalated=escalated)
        return escalated

    async def get_stats(self) -> dict[str, Any]:
        """Return aggregate debt statistics."""
        if self._driver is not None:
            async with self._driver.session() as session:
                result = await session.run(
                    """
                    MATCH (f:Finding)
                    WHERE f.status IN ['open', 'regressed']
                    RETURN f.severity AS severity, count(f) AS cnt
                    """
                )
                counts: dict[str, int] = {}
                async for record in result:
                    counts[record["severity"]] = record["cnt"]
                return {
                    "total_open": sum(counts.values()),
                    "by_severity": counts,
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                }
        return {"total_open": 0, "by_severity": {}}

    # ── Hash ────────────────────────────────
    @staticmethod
    def _compute_hash(finding: dict[str, Any]) -> str:
        """SHA-256 of tool + rule + file + message (dedup key)."""
        payload = (
            f"{finding.get('tool', '')}:"
            f"{finding.get('rule', '')}:"
            f"{finding.get('file', '')}:"
            f"{finding.get('message', '')}"
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    # ── JSON Fallback ───────────────────────
    def _upsert_json(self, findings: list[dict[str, Any]], now: str) -> int:
        self._json_path.parent.mkdir(parents=True, exist_ok=True)

        existing: dict[str, dict[str, Any]] = {}
        if self._json_path.exists():
            raw = json.loads(self._json_path.read_text(encoding="utf-8"))
            for item in raw:
                existing[item["hash"]] = item

        for finding in findings:
            fhash = self._compute_hash(finding)
            if fhash in existing:
                prev = existing[fhash]
                prev["last_seen"] = now
                prev["risk_score"] = finding.get("risk_score", 0.0)
                if prev.get("status") == "fixed":
                    prev["status"] = "regressed"
            else:
                existing[fhash] = {
                    "hash": fhash,
                    "first_seen": now,
                    "last_seen": now,
                    "status": "open",
                    **finding,
                }

        self._json_path.write_text(
            json.dumps(list(existing.values()), indent=2),
            encoding="utf-8",
        )
        return len(findings)

    def _detect_regressions_json(self) -> list[dict[str, Any]]:
        if not self._json_path.exists():
            return []
        raw = json.loads(self._json_path.read_text(encoding="utf-8"))
        return [r for r in raw if r.get("status") == "regressed"]

    # ── Health ──────────────────────────────
    async def health(self) -> dict[str, Any]:
        """Return health status for the debt graph backend."""
        if self._driver is not None:
            try:
                async with self._driver.session() as session:
                    await session.run("RETURN 1")
                return {"healthy": True, "backend": "neo4j"}
            except Exception as exc:
                logger.error("neo4j_health_failed", error=str(exc))
                return {"healthy": False, "backend": "neo4j", "error": str(exc)}
        return {"healthy": True, "backend": "json_fallback"}
