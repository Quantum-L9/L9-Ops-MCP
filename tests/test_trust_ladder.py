from l9_ops_mcp.trust_ladder import allowed_scopes


def test_l2_scopes_agent_self_resolved():
    scopes = allowed_scopes("orchestrator", "L2")
    assert "agent:orchestrator" in scopes
    assert "global:decisions" not in scopes


def test_l4_includes_decisions():
    assert "global:decisions" in allowed_scopes("planner", "L4")


def test_l5_full_graph():
    assert allowed_scopes("root", "L5") == ["*"]
