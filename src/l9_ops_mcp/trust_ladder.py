"""Trust-ladder scope resolution — maps trust level to Graphiti group_ids.

This module is the single owner of the group-id vocabulary (D-01 A).

Encoding
--------
Logical scopes are written ``<namespace>:<name>`` in doctrine (for example
``global:decisions``). graphiti-core (0.31.x) only accepts group ids matching
``^[a-zA-Z0-9_-]+$``, so every group id this service emits is encoded as
``<namespace>__<name>`` (``GROUP_SEP``). A name that contains characters outside
that alphabet (e.g. an agent id ``claude.code``) is sanitized and suffixed with
a short sha256 of the original so distinct names never collide.

Legacy data / one-time migration (U-01, not executed)
-----------------------------------------------------
Before D-01 the service attempted to write ``:``-separated group ids. With
graphiti-core 0.31.x those writes were rejected, so new data cannot exist in
the old form. A store written by an older graphiti-core may still hold
``:``-separated ids; graphiti search refuses such ids, so they are unreachable
until migrated. One-time procedure for an operator against a stopped writer:

1. Back up the database.
2. For every distinct ``group_id`` containing ``:`` on nodes and relationships,
   compute ``normalize_group_id(old)`` and run (Neo4j)::

       MATCH (n) WHERE n.group_id = $old SET n.group_id = $new
       MATCH ()-[e]->() WHERE e.group_id = $old SET e.group_id = $new

3. Verify ``MATCH (n) WHERE n.group_id CONTAINS ':' RETURN count(n)`` is 0
   (and the same for relationships).

Caller input in the legacy ``namespace:name`` form is still accepted and is
encoded by :func:`normalize_group_id`.
"""

from __future__ import annotations

import hashlib
import re
from typing import cast, get_args

from .models import TrustLevel

GROUP_SEP = "__"
_LEGAL = re.compile(r"^[A-Za-z0-9_-]+$")
_ILLEGAL_CHARS = re.compile(r"[^A-Za-z0-9_-]")


def encode_component(value: str) -> str:
    """Encode one group-id component into the graphiti-legal alphabet."""
    if not value:
        msg = "group id component must be non-empty"
        raise ValueError(msg)
    if _LEGAL.match(value):
        return value
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
    return f"{_ILLEGAL_CHARS.sub('-', value)}-{digest}"


def group_id(namespace: str, name: str) -> str:
    """Return the encoded group id for the logical scope ``namespace:name``."""
    if not _LEGAL.match(namespace):
        msg = f"invalid group namespace {namespace!r}"
        raise ValueError(msg)
    return f"{namespace}{GROUP_SEP}{encode_component(name)}"


def normalize_group_id(raw: str) -> str:
    """Map caller input (encoded or legacy ``namespace:name``) to an encoded group id."""
    if ":" in raw:
        namespace, _, name = raw.partition(":")
        return group_id(namespace, name)
    if not raw or not _LEGAL.match(raw):
        msg = f"invalid group id {raw!r}: use 'namespace:name' or [A-Za-z0-9_-]+"
        raise ValueError(msg)
    return raw


GLOBAL_CONVENTIONS = group_id("global", "conventions")
GLOBAL_DECISIONS = group_id("global", "decisions")
SESSION_CURRENT = group_id("session", "current")
PLAYBOOK_HISTORY = group_id("playbook", "history")
_AGENT_SELF = "agent:self"  # placeholder substituted per caller

_SCOPES: dict[str, list[str]] = {
    "L0": [],
    "L1": [GLOBAL_CONVENTIONS],
    "L2": [GLOBAL_CONVENTIONS, _AGENT_SELF, SESSION_CURRENT],
    "L3": [GLOBAL_CONVENTIONS, _AGENT_SELF, SESSION_CURRENT, PLAYBOOK_HISTORY],
    "L4": [
        GLOBAL_CONVENTIONS,
        _AGENT_SELF,
        SESSION_CURRENT,
        PLAYBOOK_HISTORY,
        GLOBAL_DECISIONS,
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
    return [
        group_id("agent", agent_id) if s == _AGENT_SELF else s for s in _SCOPES.get(trust_level, [])
    ]
