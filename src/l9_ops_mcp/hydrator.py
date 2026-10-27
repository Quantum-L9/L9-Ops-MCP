"""Hydrator — ONLY authorized path from Graphiti to agent context window."""

from __future__ import annotations

import tiktoken

from . import budget, trust_ladder
from .graphiti_client import get_graphiti, search_edges
from .models import ContextFact, ContextSlice, RuntimePayload, TrustLevel

_enc = tiktoken.get_encoding("cl100k_base")


def _tok(text: str) -> int:
    return len(_enc.encode(text))


class ScopeNotPermittedError(ValueError):
    """A requested group is outside the caller's trust-ladder scopes."""


def _requested_groups(scopes: list[str], requested: list[str] | None) -> list[str] | None:
    """Group ids to search: the allowed scopes, or a permitted subset of them.

    ``None`` means "all groups" and is only produced for L5 (``["*"]``) without
    an explicit narrowing request.
    """
    if requested:
        groups = [trust_ladder.normalize_group_id(g) for g in requested]
        if scopes != ["*"]:
            denied = [g for g in groups if g not in scopes]
            if denied:
                msg = f"group_ids not permitted at this trust level: {', '.join(denied)}"
                raise ScopeNotPermittedError(msg)
        return groups
    return None if scopes == ["*"] else scopes


async def query(
    text: str,
    agent_id: str,
    trust_level: str,
    limit: int = 10,
    group_ids: list[str] | None = None,
) -> list[dict[str, str]]:
    """Read-only fact search under the same trust-ladder scope resolution as hydrate.

    Unknown trust levels are rejected and empty scopes (L0) return no facts,
    both before any graph access. ``group_ids`` may only narrow the allowed
    scopes.
    """
    level = trust_ladder.validate_trust_level(trust_level)
    scopes = trust_ladder.allowed_scopes(agent_id, level)
    if limit < 1:
        msg = f"limit must be >= 1, got {limit}"
        raise ValueError(msg)
    if group_ids and not scopes:
        msg = f"group_ids not permitted at trust level {level}"
        raise ScopeNotPermittedError(msg)
    if not scopes:
        return []
    groups = _requested_groups(scopes, group_ids)
    g = await get_graphiti()
    found = await search_edges(g, text, groups, limit)
    return [{"fact": e.fact, "uuid": str(e.uuid), "valid_at": str(e.valid_at)} for e in found.edges]


async def hydrate(
    task_type: str,
    agent_id: str,
    token_budget: int,
    trust_level: TrustLevel,
    session_id: str,
) -> RuntimePayload:
    trust_level = trust_ladder.validate_trust_level(trust_level)
    scopes = trust_ladder.allowed_scopes(agent_id, trust_level)
    if not scopes:
        # An empty scope list means "no groups". Graphiti treats an empty
        # group_ids list as "no filter" (all groups), so never forward it.
        return RuntimePayload(
            agent_id=agent_id,
            trust_level=trust_level,
            allowed_scopes=[],
            context_slice=ContextSlice(),
            budget_remaining_tokens=token_budget,
        )
    g = await get_graphiti()
    group_ids = _requested_groups(scopes, None)
    found = await search_edges(g, task_type, group_ids, 50)
    facts = [
        ContextFact(
            uuid=str(e.uuid),
            fact=e.fact,
            valid_at=e.valid_at,
            invalid_at=e.invalid_at,
            group_id=e.group_id,
            score=score,
            token_estimate=_tok(e.fact),
        )
        for e, score in zip(found.edges, found.scores, strict=True)
    ]
    # Most relevant first, so tier 1 (load-bearing) receives the best facts.
    facts.sort(key=lambda f: f.score, reverse=True)
    sl = budget.allocate(facts, token_budget)
    return RuntimePayload(
        agent_id=agent_id,
        trust_level=trust_level,
        allowed_scopes=scopes,
        context_slice=sl,
        budget_remaining_tokens=token_budget - sl.token_count,
        relevance_signal=found.signal,
    )
