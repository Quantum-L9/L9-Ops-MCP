from l9_ops_mcp.budget import allocate
from l9_ops_mcp.models import ContextFact


def _f(i, score, toks):
    return ContextFact(uuid=str(i), fact="x" * toks, group_id="session:current",
                       score=score, token_estimate=toks)


def test_budget_respects_cap():
    facts = [_f(i, 1.0 - i * 0.01, 100) for i in range(50)]
    s = allocate(facts, token_budget=1000)
    assert s.token_count <= int(1000 * 0.80)


def test_highest_score_first():
    facts = [_f(0, 0.2, 50), _f(1, 0.9, 50)]
    s = allocate(facts, token_budget=1000)
    all_facts = s.tier1_load_bearing + s.tier2_examples
    assert any(f.uuid == "1" for f in all_facts)
