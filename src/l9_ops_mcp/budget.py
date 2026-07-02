"""Token budget tier allocation — context_budget_kernel.v1 TIER-1/2/3."""
from __future__ import annotations

from .models import ContextFact, ContextSlice

T1, T2, T3 = 0.60, 0.15, 0.05


def _fill(facts: list[ContextFact], budget: int) -> tuple[list[ContextFact], int]:
    out, used = [], 0
    for f in sorted(facts, key=lambda x: x.score, reverse=True):
        if used + f.token_estimate <= budget:
            out.append(f)
            used += f.token_estimate
    return out, used


def allocate(facts: list[ContextFact], token_budget: int) -> ContextSlice:
    sb = int(token_budget * 0.80)
    denom = T1 + T2 + T3
    t1b = int(sb * T1 / denom)
    t2b = int(sb * T2 / denom)
    t3b = sb - t1b - t2b
    mid = max(1, len(facts) // 2)
    t1, u1 = _fill(facts[:mid] or facts, t1b)
    t2, u2 = _fill(facts[mid:], t2b)
    t3, u3 = _fill([f for f in facts if f.invalid_at is None][:20], t3b)
    return ContextSlice(
        tier1_load_bearing=t1,
        tier2_examples=t2,
        tier3_stakes=t3,
        token_count=u1 + u2 + u3,
    )
