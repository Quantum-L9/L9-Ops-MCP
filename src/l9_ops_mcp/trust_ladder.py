"""Trust-ladder scope resolution — maps trust level to Graphiti group_ids."""
from __future__ import annotations

_SCOPES: dict[str, list[str]] = {
    "L0": [],
    "L1": ["global:conventions"],
    "L2": ["global:conventions", "agent:self", "session:current"],
    "L3": ["global:conventions", "agent:self", "session:current", "playbook:history"],
    "L4": ["global:conventions", "agent:self", "session:current",
           "playbook:history", "global:decisions"],
    "L5": ["*"],
}


def allowed_scopes(agent_id: str, trust_level: str) -> list[str]:
    return [s.replace("agent:self", f"agent:{agent_id}")
            for s in _SCOPES.get(trust_level, [])]
