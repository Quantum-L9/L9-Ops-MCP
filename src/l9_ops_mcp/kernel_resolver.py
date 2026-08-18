# --- L9_META ---
# l9_schema: 1
# artifact_type: runtime_module
# component: kernel_authority_resolver
# tags: [kernel-authority, resolver, deterministic]
# retrieval: on_demand
# status: active
# --- /L9_META ---
"""Deterministic kernel authority resolver (Slice 1).

Contract (execution contract §16-§27, §33-§36):

- Applicability is decided purely from structured request fields and
  canonical repository metadata. No embeddings, LLM calls, Graphiti reads,
  fuzzy similarity, or ambient state.
- Authority may narrow but never expand. Requesting an unknown profile,
  insufficient trust, blocked lifecycle status, unsatisfied requirement,
  cycle, or over-budget closure fails closed.
- ``resolution_digest`` is a SHA-256 over the canonical JSON of the fields
  that alter normative authority — timestamps, packet IDs, and other
  transport metadata are deliberately excluded.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .kernel_models import (
    KernelBudgetExceededError,
    KernelDefinition,
    KernelDependencyCycleError,
    KernelDependencyMissingError,
    KernelDeprecatedError,
    KernelExperimentalNotAllowedError,
    KernelProfileUnknownError,
    KernelProvenance,
    KernelRequestInvalidError,
    KernelResolution,
    KernelResolutionRequest,
    KernelSchemaInvalidError,
    KernelTrustInsufficientError,
    RING_TRUST_MINIMUM,
    TRUST_ORDINALS,
)
from .kernel_registry import KernelRegistry

SCHEMA_VERSION = "1.0.0"

# Deterministic profile → canonical kernel-id set. Additive by design; the
# resolver walks dependency closure from these seeds. Slice 1 supports BUILD
# only (execution contract §17). Other profiles are documented residuals.
PROFILE_KERNELS: dict[str, tuple[str, ...]] = {
    "BUILD": ("l9_build_kernel.v1",),
}

DEFAULT_MAX_OVERLOAD_WEIGHT = 18.0  # Doctrine §8 per-session cap.
_ID_RE = re.compile(r"^[a-z][a-z0-9_]*\.v[0-9]+$")


def canonical_json(obj: Any) -> bytes:
    """Deterministic UTF-8 canonical JSON.

    Rules (execution contract §25):

    - Keys sorted at every level.
    - No trailing whitespace, ``sort_keys=True``, ``ensure_ascii=False``.
    - Compact separators (``,`` and ``:``) — no accidental platform variance.
    - Refuses tuples/sets to prevent accidental non-canonical inputs; callers
      must normalize to plain ``list`` before hashing.
    """

    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _compute_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload)).hexdigest()


class KernelResolver:
    """Deterministic authority resolver over an immutable :class:`KernelRegistry`."""

    def __init__(self, registry: KernelRegistry) -> None:
        self._registry = registry

    @property
    def registry(self) -> KernelRegistry:
        return self._registry

    def resolve(self, request: KernelResolutionRequest) -> KernelResolution:
        self._validate_request(request)

        seeds = PROFILE_KERNELS.get(request.profile.upper())
        if seeds is None:
            raise KernelProfileUnknownError(f"unknown profile: {request.profile}")

        # Slice 1: requested_kernel_ids is defined but not implemented.
        if request.requested_kernel_ids:
            raise KernelRequestInvalidError("requested_kernel_ids is not supported in Slice 1")

        selected = self._resolve_closure(seeds)
        self._enforce_lifecycle(selected, allow_experimental=request.allow_experimental)
        self._enforce_trust(selected, request.trust_level)
        total_weight = self._enforce_budget(selected, request.max_overload_weight)
        normative_context = self._project_tier1(selected)
        provenance = self._build_provenance(selected)

        normalized_request = request.normalized()
        payload = {
            "schema_version": SCHEMA_VERSION,
            "profile": request.profile.upper(),
            "consumer": request.consumer,
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
                for k in selected
            ],
            "normative_context": normative_context,
            "total_overload_weight": float(total_weight),
        }
        digest = _compute_digest(payload)

        return KernelResolution(
            schema_version=SCHEMA_VERSION,
            profile=request.profile.upper(),
            consumer=request.consumer,
            normalized_request=normalized_request,
            kernels=selected,
            provenance=provenance,
            total_overload_weight=total_weight,
            normative_context=normative_context,
            resolution_digest=digest,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_request(request: KernelResolutionRequest) -> None:
        if not request.profile:
            raise KernelRequestInvalidError("profile is required")
        if not request.consumer:
            raise KernelRequestInvalidError("consumer is required")
        if not request.objective:
            raise KernelRequestInvalidError("objective is required")
        if request.trust_level not in TRUST_ORDINALS:
            raise KernelRequestInvalidError(
                f"invalid trust_level: {request.trust_level!r} "
                f"(expected one of {sorted(TRUST_ORDINALS)})"
            )
        if request.max_overload_weight <= 0:
            raise KernelRequestInvalidError(
                f"max_overload_weight must be > 0, got {request.max_overload_weight}"
            )
        for kid in request.requested_kernel_ids:
            if not _ID_RE.match(kid):
                raise KernelRequestInvalidError(f"malformed requested_kernel_id: {kid}")

    def _resolve_closure(self, seeds: tuple[str, ...]) -> tuple[KernelDefinition, ...]:
        """Walk requires dependencies deterministically.

        Order guarantee: dependencies before dependents; kernel_id is the
        stable tie-break (execution contract §18). Cycle detection uses a
        three-colour DFS and raises :class:`KernelDependencyCycleError`.
        """

        WHITE, GREY, BLACK = 0, 1, 2
        colour: dict[str, int] = {}
        order: list[str] = []

        def visit(kid: str, path: tuple[str, ...]) -> None:
            state = colour.get(kid, WHITE)
            if state == BLACK:
                return
            if state == GREY:
                cycle_path = " -> ".join(path + (kid,))
                raise KernelDependencyCycleError(f"dependency cycle: {cycle_path}", kernel_id=kid)
            colour[kid] = GREY
            try:
                kernel = self._registry.get(kid)
            except Exception as exc:
                raise KernelDependencyMissingError(
                    f"missing required kernel: {kid}", kernel_id=kid
                ) from exc
            # Deterministic sub-traversal.
            for req in sorted(kernel.requires):
                visit(req, path + (kid,))
            colour[kid] = BLACK
            order.append(kid)

        for seed in sorted(seeds):
            visit(seed, ())

        return tuple(self._registry.get(kid) for kid in order)

    @staticmethod
    def _enforce_lifecycle(
        selected: tuple[KernelDefinition, ...], *, allow_experimental: bool
    ) -> None:
        for k in selected:
            if not k.schema_valid:
                raise KernelSchemaInvalidError(
                    f"kernel {k.kernel_id} is not schema-conformant: "
                    + "; ".join(k.schema_errors[:3]),
                    kernel_id=k.kernel_id,
                )
            if k.init_behavior_source == "absent":
                raise KernelSchemaInvalidError(
                    f"kernel {k.kernel_id} has no normative init.behavior "
                    f"or Tier-1 block; refusing to project a documentation "
                    f"surrogate as normative authority",
                    kernel_id=k.kernel_id,
                )
            if k.status == "deprecated":
                raise KernelDeprecatedError(
                    f"kernel {k.kernel_id} is deprecated and cannot load",
                    kernel_id=k.kernel_id,
                )
            if k.status == "experimental" and not allow_experimental:
                raise KernelExperimentalNotAllowedError(
                    f"kernel {k.kernel_id} is experimental and no explicit opt-in was provided",
                    kernel_id=k.kernel_id,
                )
            if k.status == "archived":
                raise KernelDeprecatedError(
                    f"kernel {k.kernel_id} is archived and cannot load",
                    kernel_id=k.kernel_id,
                )

    @staticmethod
    def _enforce_trust(selected: tuple[KernelDefinition, ...], trust_level: str) -> None:
        caller_ord = TRUST_ORDINALS[trust_level]
        for k in selected:
            required = RING_TRUST_MINIMUM.get(k.ring)
            if required is None:
                raise KernelSchemaInvalidError(
                    f"kernel {k.kernel_id} has unknown ring: {k.ring}",
                    kernel_id=k.kernel_id,
                )
            required_ord = TRUST_ORDINALS[required]
            if caller_ord < required_ord:
                raise KernelTrustInsufficientError(
                    f"kernel {k.kernel_id} ({k.ring}) requires >= {required}, "
                    f"caller has {trust_level}",
                    kernel_id=k.kernel_id,
                )

    @staticmethod
    def _enforce_budget(
        selected: tuple[KernelDefinition, ...], max_overload_weight: float
    ) -> float:
        total = round(sum(float(k.overload_weight) for k in selected), 6)
        if total > float(max_overload_weight):
            raise KernelBudgetExceededError(
                f"required kernels overload_weight={total} exceeds budget={max_overload_weight}"
            )
        return total

    @staticmethod
    def _project_tier1(selected: tuple[KernelDefinition, ...]) -> dict[str, Any]:
        """Bounded Tier-1 projection (execution contract §21, doctrine §6).

        Emits per selected kernel:

        - identity (``kernel_id``, ``version``, ``canonical_path``, ``sha256``);
        - lifecycle (``ring``, ``activation_phase``, ``status``);
        - the normative ``init_behavior`` string and its mechanical source
          label (``init.behavior`` for YAML kernels, ``tier1_block`` for
          Markdown kernels);
        - the ``hard_bans`` list;
        - the documentation ``purpose`` (Trigger Triad summary) as a
          human-readable adjunct that is NOT normative.

        Full Tier-2/Tier-3 doctrine is not included — later slices will add
        an explicit ``disclosure_tier`` request field.

        Selection contract: a kernel that reaches projection with
        ``init_behavior_source == "absent"`` is a schema defect. The
        resolver's :meth:`_enforce_lifecycle` catches this earlier by
        refusing selection of any kernel whose canonical artifact lacks a
        normative init directive; this method assumes that guard already
        ran and asserts the invariant.
        """

        for k in selected:
            assert k.init_behavior_source != "absent", (
                f"projection invariant violated: kernel {k.kernel_id} "
                f"reached Tier-1 with no init.behavior source; lifecycle "
                f"gate should have refused it"
            )

        return {
            "kernels": [
                {
                    "kernel_id": k.kernel_id,
                    "version": k.version,
                    "ring": k.ring,
                    "activation_phase": k.activation_phase,
                    "status": k.status,
                    "init_behavior": k.init_behavior,
                    "init_behavior_source": k.init_behavior_source,
                    "hard_bans": list(k.hard_bans),
                    "purpose": k.purpose,
                    "canonical_path": k.canonical_path,
                    "sha256": k.sha256,
                }
                for k in selected
            ],
        }

    @staticmethod
    def _build_provenance(
        selected: tuple[KernelDefinition, ...],
    ) -> tuple[KernelProvenance, ...]:
        return tuple(
            KernelProvenance(
                kernel_id=k.kernel_id,
                version=k.version,
                canonical_path=k.canonical_path,
                indexed_sha256=k.sha256,
                verified_sha256=k.sha256,
            )
            for k in selected
        )
