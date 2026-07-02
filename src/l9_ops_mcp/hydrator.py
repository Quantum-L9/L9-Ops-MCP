"""Hydrator — ONLY authorized path from Graphiti to agent context window."""
from __future__ import annotations

import tiktoken

from . import budget, trust_ladder
from .graphiti_client import get_graphiti
from .models import ContextFact, RuntimePayload, TrustLevel

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
    scopes = trust_ladder.allowed_scopes(agent_id, trust_level)
    g = await get_graphiti()
    group_ids = None if scopes == ["*"] else scopes
    results = await g.search(query=task_type, group_ids=group_ids, num_results=50)
    facts = [
        ContextFact(
            uuid=str(getattr(r, "uuid", "")),
            fact=r.fact,
            valid_at=getattr(r, "valid_at", None),
            invalid_at=getattr(r, "invalid_at", None),
            group_id=(getattr(r, "group_ids", None) or [""])[0],
            score=float(getattr(r, "score", 0) or 0),
            token_estimate=_tok(r.fact),
        )
        for r in results
    ]
    sl = budget.allocate(facts, token_budget)
    return RuntimePayload(
        agent_id=agent_id,
        trust_level=trust_level,
        allowed_scopes=scopes,
        context_slice=sl,
        budget_remaining_tokens=token_budget - sl.token_count,
    )
