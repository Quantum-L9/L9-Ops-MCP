# --- L9_META ---
# l9_schema: 1
# component: ai_enrichment_engine
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

"""L11 AI Enrichment Engine (Perplexity Integration).

Non-blocking semantic analysis and classification layer.
Circuit breaker falls back to deterministic-only on API failure.

DORA:
    component_id: l11-ai-enrichment-engine
    tier: 2
    lifecycle: production
    owner: platform-engineering
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


class CircuitBreaker:
    """Simple circuit breaker for external API calls.

    ADR Compliance:
        ADR-0009  Circuit breaker resilience
    """

    def __init__(self, threshold: int = 5, cooldown: int = 300) -> None:
        self.threshold = threshold
        self.cooldown = cooldown
        self.failure_count = 0
        self.last_failure_time: datetime | None = None

    def is_open(self) -> bool:
        """Return True when circuit is open (API should not be called).

        Pure read: after the cooldown the breaker is half-open and allows a
        trial call; a failed trial re-opens it, a success closes it.
        """
        return self.state == "open"

    def record_failure(self) -> None:
        """Record an API failure."""
        self.failure_count += 1
        self.last_failure_time = datetime.now(tz=timezone.utc)
        logger.warning(
            "circuit_breaker_failure",
            failure_count=self.failure_count,
            threshold=self.threshold,
        )

    def record_success(self) -> None:
        """Record an API success (resets failure counter)."""
        self.failure_count = 0
        self.last_failure_time = None

    @property
    def state(self) -> str:
        """Return the breaker phase: ``closed``, ``open`` or ``half-open``.

        Derived from the failure count and cooldown; never mutates state.
        """
        if self.failure_count < self.threshold or self.last_failure_time is None:
            return "closed"
        elapsed = (datetime.now(tz=timezone.utc) - self.last_failure_time).total_seconds()
        if elapsed >= self.cooldown:
            return "half-open"
        return "open"


class AIEnrichmentEngine:
    """AI-powered enrichment using Perplexity sonar-pro.

    ADR Compliance:
        ADR-0019  structlog-only logging
        ADR-0009  Circuit breaker for external API
        ADR-0083  UTC datetime standard
    """

    API_BASE = "https://api.perplexity.ai/chat/completions"

    def __init__(self, config: dict[str, Any]) -> None:
        ai_cfg = config["detection"]["ai_layer"]
        self.model: str = ai_cfg.get("model", "sonar-pro")
        self.api_key: str | None = os.getenv(ai_cfg.get("api_key_env", "PERPLEXITY_API_KEY"))

        cb_cfg = ai_cfg.get("circuit_breaker", {})
        self.circuit_breaker = CircuitBreaker(
            threshold=cb_cfg.get("failure_threshold", 5),
            cooldown=cb_cfg.get("cooldown_seconds", 300),
        )

        retry_cfg = ai_cfg.get("retry_policy", {})
        self.max_attempts: int = retry_cfg.get("max_attempts", 3)

        cost_cfg = ai_cfg.get("cost_control", {})
        self.rate_limit_rpm: int = cost_cfg.get("rate_limit_rpm", 60)

        chunk_cfg = ai_cfg.get("chunking", {})
        self.max_tokens: int = chunk_cfg.get("max_tokens", 2500)

    # ── Public API ──────────────────────────
    async def enqueue_enrichment(self, findings: list[dict[str, Any]]) -> None:
        """Queue findings for asynchronous enrichment.

        In production this pushes to a Redis/Celery priority queue.
        Here it processes inline for simplicity.
        """
        logger.info("enrichment_queued", findings_count=len(findings))
        await self.enrich_batch(findings)

    async def enrich_batch(self, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Enrich a batch of findings with AI classification.

        Returns the same findings with an ``ai_enrichment`` dict added.  On any
        failure (missing key, open breaker, transport error, malformed
        response) the finding is returned with ``ai_enrichment.enriched`` False.
        """
        if not self.api_key:
            logger.warning("ai_api_key_missing")
            return [self._fallback(f, "api_key_missing") for f in findings]

        enriched: list[dict[str, Any]] = []
        for finding in findings:
            # Consult the breaker before every call, not once per batch.
            if self.circuit_breaker.is_open():
                logger.warning("circuit_breaker_open", state=self.circuit_breaker.state)
                enriched.append(self._fallback(finding, "circuit_breaker_open"))
                continue
            enriched.append(await self._enrich_single(finding))

        return enriched

    @staticmethod
    def _fallback(finding: dict[str, Any], reason: str) -> dict[str, Any]:
        """Mark *finding* as not enriched (deterministic-only fallback)."""
        finding["ai_enrichment"] = {"enriched": False, "reason": reason}
        return finding

    # ── Internal ────────────────────────────
    async def _enrich_single(self, finding: dict[str, Any]) -> dict[str, Any]:
        """Call Perplexity API to classify one finding."""
        prompt = self._build_prompt(finding)

        last_error = "no_attempt"
        for attempt in range(1, self.max_attempts + 1):
            if self.circuit_breaker.is_open():
                return self._fallback(finding, "circuit_breaker_open")
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        self.API_BASE,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.model,
                            "messages": [
                                {
                                    "role": "system",
                                    "content": (
                                        "You are a technical debt classifier. "
                                        "Respond with JSON: "
                                        '{"category":"...","blast_radius":"...","remediation":"..."}'
                                    ),
                                },
                                {"role": "user", "content": prompt},
                            ],
                        },
                    )
                resp.raise_for_status()

                content = resp.json()["choices"][0]["message"]["content"]
                parsed = self._parse_ai_response(content)

                finding["ai_enrichment"] = {
                    **parsed,
                    "enriched": True,
                    "model": self.model,
                    "enriched_at": datetime.now(tz=timezone.utc).isoformat(),
                }
                self.circuit_breaker.record_success()
                return finding

            # httpx.HTTPError covers every transport error, timeout and status
            # error; ValueError covers a non-JSON body (json.JSONDecodeError);
            # KeyError/IndexError/TypeError cover a malformed response shape.
            except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "ai_enrichment_attempt_failed",
                    attempt=attempt,
                    error=last_error,
                )
                if attempt == self.max_attempts:
                    self.circuit_breaker.record_failure()

        return self._fallback(finding, last_error)

    def _build_prompt(self, finding: dict[str, Any]) -> str:
        """Build the enrichment prompt for one finding."""
        return (
            f"Analyze this technical debt finding:\n\n"
            f"Tool: {finding.get('tool', 'unknown')}\n"
            f"Rule: {finding.get('rule', 'N/A')}\n"
            f"Message: {finding.get('message', '')}\n"
            f"Severity: {finding.get('severity', 'P3')}\n"
            f"File: {finding.get('file', '')}\n\n"
            f"Return JSON with keys: category, blast_radius, remediation."
        )

    def _parse_ai_response(self, content: str) -> dict[str, str]:
        """Best-effort parse AI response into structured fields."""
        try:
            # Try JSON parse first
            start = content.index("{")
            end = content.rindex("}") + 1
            return json.loads(content[start:end])
        except (ValueError, json.JSONDecodeError):
            pass

        # Heuristic fallback
        lower = content.lower()
        category = "maintainability"
        if "security" in lower:
            category = "security"
        elif "performance" in lower:
            category = "performance"
        elif "reliability" in lower:
            category = "reliability"

        blast_radius = "isolated"
        if "system" in lower:
            blast_radius = "system-wide"
        elif "module" in lower:
            blast_radius = "module"

        return {
            "category": category,
            "blast_radius": blast_radius,
            "remediation": content[:200].strip(),
        }

    # ── Health ──────────────────────────────
    async def health(self) -> dict[str, Any]:
        """Return AI engine health status."""
        return {
            "healthy": not self.circuit_breaker.is_open(),
            "circuit_breaker_state": self.circuit_breaker.state,
            "api_key_configured": self.api_key is not None,
            "model": self.model,
        }
