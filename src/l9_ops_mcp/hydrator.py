"""The Hydrator: the ONLY authorized path from graph/memory to agent context.

Implements context_budget_kernel.v1 hydrator_contract assembly_order:
  1 resolve trust_level  2 fetch allowed_scopes  3 pull graph slice
  4 apply budget tiers    5 compress >80%         6 seal read-only  7 emit
Resolves U-H1 (impl language: Python) and U-H2 (backend: Graphiti).
"""
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
    # 1 + 2: trust -> allowed scopes
    scopes = trust_ladder.allowed_scopes(agent_id, trust_level)

    # 3: pull task-scoped graph slice via Graphiti
    g = await get_graphiti()
    group_ids = None if scopes == ["*"] else scopes
    results = await g.search(query=task_type, group_ids=group_ids, num_results=50)

    facts = [
        ContextFact(
            uuid=getattr(r, "uuid", ""),
            fact=r.fact,
            valid_at=getattr(r, "valid_at", None),
            invalid_at=getattr(r, "invalid_at", None),
            group_id=(getattr(r, "group_ids", None) or [""])[0],
            score=getattr(r, "score", 0.0) or 0.0,
            token_estimate=_tok(r.fact),
        )
        for r in results
    ]

    # 4 + 5: tier allocation with compression built into the budget cap
    context_slice = budget.allocate(facts, token_budget)

    # 6 + 7: seal as read-only RuntimePayload
    return RuntimePayload(
        agent_id=agent_id,
        trust_level=trust_level,
        allowed_scopes=scopes,
        context_slice=context_slice,
        budget_remaining_tokens=token_budget - context_slice.token_count,
    )
