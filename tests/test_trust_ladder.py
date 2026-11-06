# >>> l9:meta >>>
# id: L9-Ops-MCP.test.tests_test_trust_ladder__py
# title: test trust ladder
# artifact_type: test
# mcp_primitive: none
# callable: false
# retrievable: false
# injectable: false
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: tests/test_trust_ladder.py
# content_hash: 8f6abc04843cb0b885ff1659522463b7e792e810207efcd0037221d5ac634ed7
# token_cost_estimate: 149
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
"""Unit tests for trust-ladder scope resolution."""

from l9_ops_mcp.trust_ladder import allowed_scopes


def test_l0_empty():
    assert allowed_scopes("any", "L0") == []


def test_l2_resolves_self():
    scopes = allowed_scopes("orchestrator", "L2")
    assert "agent:orchestrator" in scopes
    assert "global:decisions" not in scopes


def test_l4_includes_decisions():
    assert "global:decisions" in allowed_scopes("planner", "L4")


def test_l5_full_graph():
    assert allowed_scopes("root", "L5") == ["*"]


def test_unknown_level_empty():
    assert allowed_scopes("x", "L99") == []
