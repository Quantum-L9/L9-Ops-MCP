"""Unit tests for token budget tier allocation."""

from l9_ops_mcp.budget import allocate
from l9_ops_mcp.models import ContextFact


def _f(i: int, score: float, toks: int) -> ContextFact:
    return ContextFact(
        uuid=str(i), fact="x" * toks, group_id="session:current", score=score, token_estimate=toks
    )


def test_respects_80pct_cap():
    facts = [_f(i, 1.0 - i * 0.01, 100) for i in range(50)]
    s = allocate(facts, token_budget=1000)
    assert s.token_count <= int(1000 * 0.80)


def test_highest_score_selected():
    facts = [_f(0, 0.2, 50), _f(1, 0.9, 50)]
    s = allocate(facts, token_budget=1000)
    all_facts = s.tier1_load_bearing + s.tier2_examples
    assert any(f.uuid == "1" for f in all_facts)


def test_empty_facts_returns_zero_slice():
    s = allocate([], token_budget=1000)
    assert s.token_count == 0


def test_budget_zero_returns_empty():
    facts = [_f(0, 1.0, 100)]
    s = allocate(facts, token_budget=0)
    assert s.token_count == 0


# --- RG-07: tiers are disjoint and token_count counts each injected fact once ---


def _uuids(s):
    return [f.uuid for f in s.tier1_load_bearing + s.tier2_examples + s.tier3_stakes]


def test_tiers_disjoint_on_ten_facts():
    facts = [_f(i, 1.0 - i * 0.05, 5) for i in range(10)]
    s = allocate(facts, token_budget=1000)
    ids = _uuids(s)
    assert len(ids) == len(set(ids)), f"duplicate facts across tiers: {ids}"


def test_token_count_equals_distinct_injected_tokens():
    facts = [_f(0, 0.9, 5), _f(1, 0.8, 6)]
    s = allocate(facts, token_budget=1000)
    injected = s.tier1_load_bearing + s.tier2_examples + s.tier3_stakes
    assert s.token_count == sum(f.token_estimate for f in injected)
    assert s.token_count == 11


def test_tier3_takes_only_unselected_valid_facts():
    # tier1/tier2 budgets are small, so leftover valid facts can land in tier3
    facts = [_f(i, 1.0 - i * 0.01, 40) for i in range(6)]
    s = allocate(facts, token_budget=100)
    ids = _uuids(s)
    assert len(ids) == len(set(ids))
    assert s.token_count <= int(100 * 0.80)
