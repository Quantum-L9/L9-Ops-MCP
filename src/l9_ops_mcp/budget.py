"""Context budget tier allocation (context_budget_kernel.v1).

TIER-1 load-bearing 60% | TIER-2 examples 15% | TIER-3 stakes 5%
TIER-4 request 10% (reserved by caller) | TIER-5 model output 10% (reserved).
Compresses when consumption exceeds 80% of the context slice budget.
"""
from __future__ import annotations

from .models import ContextFact, ContextSlice

TIER1_FRAC = 0.60
TIER2_FRAC = 0.15
TIER3_FRAC = 0.05
COMPRESS_THRESHOLD = 0.80


def _fill(facts: list[ContextFact], budget: int) -> tuple[list[ContextFact], int]:
    out, used = [], 0
    for f in sorted(facts, key=lambda x: x.score, reverse=True):
        if used + f.token_estimate > budget:
            continue
        out.append(f)
        used += f.token_estimate
    return out, used


def allocate(facts: list[ContextFact], token_budget: int) -> ContextSlice:
    # Reserve 20% (TIER-4 request + TIER-5 output) for the caller.
    slice_budget = int(token_budget * 0.80)
    t1_b = int(slice_budget * TIER1_FRAC / (TIER1_FRAC + TIER2_FRAC + TIER3_FRAC))
    t2_b = int(slice_budget * TIER2_FRAC / (TIER1_FRAC + TIER2_FRAC + TIER3_FRAC))
    t3_b = slice_budget - t1_b - t2_b

    ranked = sorted(facts, key=lambda x: x.score, reverse=True)
    tier1_src = ranked[: len(ranked) // 2] or ranked
    tier2_src = ranked[len(ranked) // 2 :]
    tier3_src = [f for f in ranked if f.invalid_at is None][:20]  # active constraints

    t1, u1 = _fill(tier1_src, t1_b)
    t2, u2 = _fill(tier2_src, t2_b)
    t3, u3 = _fill(tier3_src, t3_b)

    return ContextSlice(
        tier1_load_bearing=t1,
        tier2_examples=t2,
        tier3_stakes=t3,
        token_count=u1 + u2 + u3,
    )
