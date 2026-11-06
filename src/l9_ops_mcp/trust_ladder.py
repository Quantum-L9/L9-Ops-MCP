# >>> l9:meta >>>
# id: L9-Ops-MCP.source.src_l9_ops_mcp_trust_ladder__py
# title: trust ladder
# artifact_type: source
# mcp_primitive: resource
# callable: false
# retrievable: true
# injectable: true
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: src/l9_ops_mcp/trust_ladder.py
# content_hash: a3a8abc227293044a351b35a176852a2a987b65089efa90f248e7208711c81a7
# token_cost_estimate: 172
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
"""Trust-ladder scope resolution — maps trust level to Graphiti group_ids."""

from __future__ import annotations

_SCOPES: dict[str, list[str]] = {
    "L0": [],
    "L1": ["global:conventions"],
    "L2": ["global:conventions", "agent:self", "session:current"],
    "L3": ["global:conventions", "agent:self", "session:current", "playbook:history"],
    "L4": [
        "global:conventions",
        "agent:self",
        "session:current",
        "playbook:history",
        "global:decisions",
    ],
    "L5": ["*"],
}


def allowed_scopes(agent_id: str, trust_level: str) -> list[str]:
    return [s.replace("agent:self", f"agent:{agent_id}") for s in _SCOPES.get(trust_level, [])]
