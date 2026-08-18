# --- L9_META ---
# l9_schema: 1
# artifact_type: runtime_module
# component: kernel_authority_models
# tags: [kernel-authority, models, canonical]
# retrieval: on_demand
# status: active
# --- /L9_META ---
"""Typed domain models for the L9 kernel authority plane (Slice 1).

This module owns typed domain models only. It performs no I/O, imports no
Graphiti / Neo4j / LLM / memory modules, and encodes no profile-to-kernel
routing policy. Registry discovery lives in :mod:`kernel_registry`;
applicability policy lives in :mod:`kernel_resolver`.

Determinism boundary
--------------------

Fields consumed by :class:`KernelResolution.resolution_digest` MUST be listed
in :func:`canonical_resolution_payload`. Transport/runtime metadata (packet
IDs, timestamps, hostnames) is deliberately excluded from the digestable
representation and is added only by the outer TransportPacket envelope.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


TRUST_ORDINALS: dict[str, int] = {
    "L0": 0,
    "L1": 1,
    "L2": 2,
    "L3": 3,
    "L4": 4,
    "L5": 5,
}

RING_TRUST_MINIMUM: dict[str, str] = {
    # From docs/KERNEL_DOCTRINE.md §9 (v3.4.1).
    "R0": "L0",
    "R1": "L0",
    "R2": "L1",
    "R3": "L1",
    "R4": "L2",
    "R5": "L3",
    "R6": "L2",
}

VALID_STATUS = frozenset({"active", "experimental", "deprecated", "archived"})
VALID_ACTIVATION_PHASE = frozenset({"always", "on_demand", "lazy"})


class KernelAuthorityError(Exception):
    """Base class for stable, machine-actionable kernel authority failures.

    ``code`` values are the contract taxonomy (see execution contract §15 and
    §33). MCP callers must observe the ``code`` string, not the message.
    """

    code: str = "KERNEL_ERROR"

    def __init__(self, message: str, *, kernel_id: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.kernel_id = kernel_id

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": "error",
            "code": self.code,
            "message": self.message,
        }
        if self.kernel_id is not None:
            payload["kernel_id"] = self.kernel_id
        return payload


class KernelNotFoundError(KernelAuthorityError):
    code = "KERNEL_NOT_FOUND"


class KernelSchemaInvalidError(KernelAuthorityError):
    code = "KERNEL_SCHEMA_INVALID"


class KernelIndexEntryMissingError(KernelAuthorityError):
    code = "KERNEL_INDEX_ENTRY_MISSING"


class KernelDigestMismatchError(KernelAuthorityError):
    code = "KERNEL_DIGEST_MISMATCH"


class KernelDuplicateIdError(KernelAuthorityError):
    code = "KERNEL_DUPLICATE_ID"


class KernelDeprecatedError(KernelAuthorityError):
    code = "KERNEL_DEPRECATED"


class KernelExperimentalNotAllowedError(KernelAuthorityError):
    code = "KERNEL_EXPERIMENTAL_NOT_ALLOWED"


class KernelTrustInsufficientError(KernelAuthorityError):
    code = "KERNEL_TRUST_INSUFFICIENT"


class KernelDependencyMissingError(KernelAuthorityError):
    code = "KERNEL_DEPENDENCY_MISSING"


class KernelDependencyCycleError(KernelAuthorityError):
    code = "KERNEL_DEPENDENCY_CYCLE"


class KernelBudgetExceededError(KernelAuthorityError):
    code = "KERNEL_BUDGET_EXCEEDED"


class KernelProfileUnknownError(KernelAuthorityError):
    code = "KERNEL_PROFILE_UNKNOWN"


class KernelConflictError(KernelAuthorityError):
    code = "KERNEL_CONFLICT"


class KernelRequestInvalidError(KernelAuthorityError):
    code = "KERNEL_REQUEST_INVALID"


@dataclass(frozen=True)
class KernelDefinition:
    """One validated canonical kernel.

    ``schema_valid`` records the result of the two-phase validation. Registry
    load parses every discovered kernel and retains unknown metadata (see
    execution contract §7.1). Resolvers refuse to select kernels where
    ``schema_valid`` is False (see §33 failure semantics).
    """

    kernel_id: str
    version: str
    ring: str
    category: str
    title: str
    purpose: str
    activation_phase: str
    status: str
    overload_weight: float
    hard_bans: tuple[str, ...]
    fail_closed: bool
    requires: tuple[str, ...]
    routing_hints: dict[str, Any]
    canonical_path: str
    sha256: str
    schema_valid: bool
    # Normative init directive block projected as the doctrine §6 Tier-1
    # ``init.behavior`` payload. Sourced mechanically from either the YAML
    # ``init.behavior`` field or a Markdown ``## TIER 1`` body. Never
    # derived from ``purpose`` (documentation) or ``title`` (label).
    init_behavior: str = ""
    # Mechanical label recording which source produced ``init_behavior``.
    # One of: ``init.behavior``, ``tier1_block``, ``absent``.
    init_behavior_source: str = "absent"
    schema_errors: tuple[str, ...] = field(default_factory=tuple)
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KernelProvenance:
    """Provenance record sufficient for a PE consumer to re-pin authority."""

    kernel_id: str
    version: str
    canonical_path: str
    indexed_sha256: str
    verified_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "kernel_id": self.kernel_id,
            "version": self.version,
            "canonical_path": self.canonical_path,
            "indexed_sha256": self.indexed_sha256,
            "verified_sha256": self.verified_sha256,
        }


@dataclass(frozen=True)
class KernelResolutionRequest:
    """Structured resolution request.

    Slice 1 rejects unknown top-level fields at MCP boundary (see server.py).
    ``requested_kernel_ids`` is defined but Slice 1 does not implement it;
    callers passing a non-empty value get ``KERNEL_REQUEST_INVALID``.
    """

    profile: str
    consumer: str
    objective: str
    trust_level: str
    max_overload_weight: float
    requested_kernel_ids: tuple[str, ...] = ()
    allow_experimental: bool = False

    def normalized(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "consumer": self.consumer,
            "objective": self.objective,
            "trust_level": self.trust_level,
            "max_overload_weight": float(self.max_overload_weight),
            "requested_kernel_ids": list(self.requested_kernel_ids),
            "allow_experimental": bool(self.allow_experimental),
        }


@dataclass(frozen=True)
class KernelResolution:
    """Deterministic kernel-authority resolution result.

    ``resolution_digest`` is computed from :func:`canonical_resolution_payload`
    and never depends on wall clock, packet IDs, hostnames, PIDs, mtimes, or
    absolute checkout paths. Two resolver instances resolving the same repo
    state MUST produce the same digest.
    """

    schema_version: str
    profile: str
    consumer: str
    normalized_request: dict[str, Any]
    kernels: tuple[KernelDefinition, ...]
    provenance: tuple[KernelProvenance, ...]
    total_overload_weight: float
    normative_context: dict[str, Any]
    resolution_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "profile": self.profile,
            "consumer": self.consumer,
            "normalized_request": self.normalized_request,
            "resolution_digest": self.resolution_digest,
            "total_overload_weight": self.total_overload_weight,
            "kernels": [
                {
                    "kernel_id": k.kernel_id,
                    "version": k.version,
                    "ring": k.ring,
                    "category": k.category,
                    "activation_phase": k.activation_phase,
                    "canonical_path": k.canonical_path,
                    "sha256": k.sha256,
                    "overload_weight": k.overload_weight,
                    "tier": 1,
                }
                for k in self.kernels
            ],
            "provenance": [p.to_dict() for p in self.provenance],
            "normative_context": self.normative_context,
        }


def canonical_resolution_payload(
    *,
    schema_version: str,
    profile: str,
    consumer: str,
    normalized_request: dict[str, Any],
    kernels: tuple[KernelDefinition, ...],
    normative_context: dict[str, Any],
    total_overload_weight: float,
) -> dict[str, Any]:
    """Return the exact object that :func:`canonical_json` will hash.

    Ordering rules
    --------------
    - Kernels are emitted in the deterministic order supplied by the resolver
      (dependency closure with kernel_id tie-break; see resolver §18).
    - Only fields that alter normative authority are included.
    - Numeric ``overload_weight`` is coerced to a float to remove int/float
      accidental differences.
    """

    return {
        "schema_version": schema_version,
        "profile": profile,
        "consumer": consumer,
        "normalized_request": normalized_request,
        "kernels": [
            {
                "kernel_id": k.kernel_id,
                "version": k.version,
                "ring": k.ring,
                "activation_phase": k.activation_phase,
                "status": k.status,
                "overload_weight": float(k.overload_weight),
                "canonical_path": k.canonical_path,
                "sha256": k.sha256,
                "tier": 1,
            }
            for k in kernels
        ],
        "normative_context": normative_context,
        "total_overload_weight": float(total_overload_weight),
    }
