"""Trust-ladder scope resolution (trust_ladder_kernel.v1).

Maps an agent trust level to the memory/graph scopes (group_ids) it may read.
Namespaces mirror the agents-project-memory skill contract.
"""
from __future__ import annotations

_SCOPE_MATRIX: dict[str, list[str]] = {
    "L0": [],
    "L1": ["global:conventions"],
    "L2": ["global:conventions", "agent:self", "session:current"],
    "L3": ["global:conventions", "agent:self", "session:current", "playbook:history"],
    "L4": ["global:conventions", "agent:self", "session:current",
           "playbook:history", "global:decisions"],
    "L5": ["*"],  # full graph
}


def allowed_scopes(agent_id: str, trust_level: str) -> list[str]:
    scopes = _SCOPE_MATRIX.get(trust_level, [])
    return [s.replace("agent:self", f"agent:{agent_id}") for s in scopes]
