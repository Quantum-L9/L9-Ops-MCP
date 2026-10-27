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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

#: Rule a producer uses for a check that could not run.  Such a tool cannot
#: vouch that its earlier findings are gone, so they are never marked fixed.
ENGINE_ERROR_RULE = "engine_error"

#: Statuses counted as live debt (stats) and eligible to become ``fixed``.
LIVE_STATUSES = ("open", "regressed")


def scope_prefixes(scope: list[str]) -> list[str]:
    """Normalise scan scope entries to path prefixes (relative and absolute)."""
    prefixes: set[str] = set()
    for entry in scope:
        if not entry:
            continue
        prefixes.add(os.path.normpath(entry))
        prefixes.add(os.path.normpath(os.path.abspath(entry)))
    return sorted(prefixes)


def in_scope(file: str, prefixes: list[str]) -> bool:
    """True when *file* equals a prefix or lies under one (same rule as Cypher)."""
    return bool(file) and any(file == p or file.startswith(p + "/") for p in prefixes)


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
        self._fallback_reason: str | None = None

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
                    self._fallback_reason = "neo4j_env_missing"
                    logger.warning("neo4j_env_missing")
            except ImportError:
                self._fallback_reason = "neo4j_driver_not_installed"
                logger.warning("neo4j_driver_not_installed")

        # JSON fallback config
        fb_cfg = config["state_management"].get("json_fallback", {})
        self._json_path = Path(fb_cfg.get("path", ".l11/debt_findings.json"))

        aging_cfg = config["risk_model"].get("aging_policy", {})
        self._p2_to_p1_days: int = aging_cfg.get("p2_to_p1_days", 30)
        self._p1_to_p0_days: int = aging_cfg.get("p1_to_p0_days", 60)

    # ── Public API ──────────────────────────
    async def upsert_findings(
        self,
        findings: list[dict[str, Any]],
        *,
        scope: list[str] | None = None,
    ) -> int:
        """Upsert findings with deduplication by content hash.

        When *scope* is given, *findings* is the complete result of a scan of
        that scope: live records whose file lies in the scope and whose hash is
        absent become ``fixed`` (unless their tool reported ``engine_error`` in
        this scan).  A later reappearance turns a ``fixed`` record ``regressed``.

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
        if scope is not None:
            fixed = await self._mark_absent_fixed(findings, scope, now)
            logger.info("findings_marked_fixed", count=fixed, scope=scope)
        return upserted

    async def _mark_absent_fixed(
        self,
        findings: list[dict[str, Any]],
        scope: list[str],
        now: str,
    ) -> int:
        """Transition live in-scope records absent from *findings* to ``fixed``."""
        hashes = [self._compute_hash(f) for f in findings]
        prefixes = scope_prefixes(scope)
        skip_tools = sorted(
            {str(f.get("tool", "")) for f in findings if f.get("rule") == ENGINE_ERROR_RULE}
        )
        if not prefixes:
            return 0

        if self._driver is not None:
            async with self._driver.session() as session:
                result = await session.run(
                    """
                    MATCH (f:Finding)
                    WHERE f.status IN ['open', 'regressed']
                      AND NOT f.hash IN $hashes
                      AND NOT f.tool IN $skip_tools
                      AND any(p IN $prefixes WHERE f.file = p OR f.file STARTS WITH p + '/')
                    SET f.status = 'fixed', f.fixed_at = datetime($now)
                    RETURN count(f) AS cnt
                    """,
                    {
                        "hashes": hashes,
                        "skip_tools": skip_tools,
                        "prefixes": prefixes,
                        "now": now,
                    },
                )
                rec = await result.single()
                return int(rec["cnt"]) if rec else 0

        records = self._load_json()
        present = set(hashes)
        fixed = 0
        for rec in records:
            if (
                rec.get("status") in LIVE_STATUSES
                and rec.get("hash") not in present
                and str(rec.get("tool", "")) not in skip_tools
                and in_scope(str(rec.get("file") or ""), prefixes)
            ):
                rec["status"] = "fixed"
                rec["fixed_at"] = now
                fixed += 1
        if fixed:
            self._save_json(records)
        return fixed

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
        else:
            escalated = self._apply_aging_json()

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
        json_counts: dict[str, int] = {}
        for rec in self._load_json():
            if rec.get("status") in LIVE_STATUSES:
                sev = rec.get("severity", "P3")
                json_counts[sev] = json_counts.get(sev, 0) + 1
        return {
            "total_open": sum(json_counts.values()),
            "by_severity": json_counts,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

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
    def _load_json(self) -> list[dict[str, Any]]:
        if not self._json_path.exists():
            return []
        raw = json.loads(self._json_path.read_text(encoding="utf-8"))
        return list(raw)

    def _save_json(self, records: list[dict[str, Any]]) -> None:
        self._json_path.parent.mkdir(parents=True, exist_ok=True)
        self._json_path.write_text(json.dumps(records, indent=2), encoding="utf-8")

    def _apply_aging_json(self) -> int:
        """Same transitions and order as the Neo4j queries (P2→P1, then P1→P0)."""
        records = self._load_json()
        now = datetime.now(tz=timezone.utc)
        escalated = 0
        for from_sev, to_sev, days in (
            ("P2", "P1", self._p2_to_p1_days),
            ("P1", "P0", self._p1_to_p0_days),
        ):
            cutoff = now - timedelta(days=days)
            for rec in records:
                if rec.get("severity") != from_sev or rec.get("status") != "open":
                    continue
                first_seen = datetime.fromisoformat(str(rec["first_seen"]))
                if first_seen.tzinfo is None:
                    first_seen = first_seen.replace(tzinfo=timezone.utc)
                if first_seen < cutoff:
                    rec["severity"] = to_sev
                    escalated += 1
        if escalated:
            self._save_json(records)
        return escalated

    def _upsert_json(self, findings: list[dict[str, Any]], now: str) -> int:
        existing: dict[str, dict[str, Any]] = {}
        for item in self._load_json():
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

        self._save_json(list(existing.values()))
        return len(findings)

    def _detect_regressions_json(self) -> list[dict[str, Any]]:
        return [r for r in self._load_json() if r.get("status") == "regressed"]

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
        if self._backend == "neo4j":
            # Neo4j was configured but is not in use: report it, do not hide it.
            return {
                "healthy": False,
                "backend": "json_fallback",
                "configured_backend": "neo4j",
                "error": self._fallback_reason or "neo4j_unavailable",
            }
        return {"healthy": True, "backend": "json_fallback", "configured_backend": self._backend}
