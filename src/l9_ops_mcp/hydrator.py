"""Hydrator — ONLY authorized path from Graphiti to agent context window."""

from __future__ import annotations

import tiktoken

from . import budget, trust_ladder
from .graphiti_client import get_graphiti, search_edges
from .models import ContextFact, ContextSlice, RuntimePayload, TrustLevel

_enc = tiktoken.get_encoding("cl100k_base")


def _tok(text: str) -> int:
    return len(_enc.encode(text))


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
    group_ids = None if scopes == ["*"] else scopes
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
