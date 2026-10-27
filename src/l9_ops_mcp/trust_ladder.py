"""Trust-ladder scope resolution — maps trust level to Graphiti group_ids."""

from __future__ import annotations

from typing import cast, get_args

from .models import TrustLevel

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

TRUST_LEVELS: tuple[str, ...] = get_args(TrustLevel)


class UnknownTrustLevelError(ValueError):
    """Raised when a trust_level is not one of L0..L5."""


def validate_trust_level(trust_level: object) -> TrustLevel:
    """Return ``trust_level`` if it is a known level, else raise before any graph access."""
    if not isinstance(trust_level, str) or trust_level not in TRUST_LEVELS:
        msg = f"invalid trust_level {trust_level!r}; expected one of {', '.join(TRUST_LEVELS)}"
        raise UnknownTrustLevelError(msg)
    return cast(TrustLevel, trust_level)


def allowed_scopes(agent_id: str, trust_level: str) -> list[str]:
    return [s.replace("agent:self", f"agent:{agent_id}") for s in _SCOPES.get(trust_level, [])]
