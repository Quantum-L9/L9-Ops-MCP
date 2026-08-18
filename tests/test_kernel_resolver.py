"""Unit tests for :mod:`l9_ops_mcp.kernel_resolver` (execution contract §41).

Uses synthetic fixture repositories in ``tmp_path`` for every adversarial
case, plus one end-to-end test against the real repository BUILD profile.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from l9_ops_mcp.kernel_models import (
    KernelBudgetExceededError,
    KernelDependencyCycleError,
    KernelDependencyMissingError,
    KernelDeprecatedError,
    KernelExperimentalNotAllowedError,
    KernelProfileUnknownError,
    KernelResolutionRequest,
    KernelRequestInvalidError,
    KernelSchemaInvalidError,
    KernelTrustInsufficientError,
)
from l9_ops_mcp.kernel_registry import KernelRegistry
from l9_ops_mcp import kernel_resolver as resolver_mod
from l9_ops_mcp.kernel_resolver import (
    KernelResolver,
)


@pytest.fixture(autouse=True)
def _isolate_profile_map(monkeypatch):
    """Snapshot and restore PROFILE_KERNELS around every test."""

    monkeypatch.setattr(
        resolver_mod,
        "PROFILE_KERNELS",
        dict(resolver_mod.PROFILE_KERNELS),
    )
    yield


CANONICAL_SCHEMA_SRC = (
    Path(__file__).resolve().parents[1] / "schemas" / "kernel.canonical.schema.json"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_yaml(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def _copy_schema(root: Path) -> None:
    dest = root / "schemas" / "kernel.canonical.schema.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(CANONICAL_SCHEMA_SRC.read_text(encoding="utf-8"), encoding="utf-8")


def _kernel(
    kernel_id: str,
    *,
    ring: str = "R5",
    weight: float = 1.0,
    requires: list[str] | None = None,
    status: str = "active",
    init_behavior: str | None = "deterministic fixture init directive",
) -> dict:
    doc: dict = {
        "kernel_id": kernel_id,
        "version": "1.0.0",
        "ring": ring,
        "category": "developer_support",
        "title": f"{kernel_id} title",
        "purpose": "WHAT / WHEN / WHY three-sentence purpose.",
        "activation_phase": "on_demand" if ring == "R5" else "always",
        "status": status,
        "overload_weight": weight,
        "hard_bans": [f"MUST NOT abuse {kernel_id}"],
        "fail_closed": True,
        "requires": requires or [],
    }
    if init_behavior is not None:
        # Fixture kernels declare the doctrine §4 canonical ``init.behavior``
        # mapping so the resolver's Tier-1 projection can emit real
        # normative content. Pass ``init_behavior=None`` to build a kernel
        # that intentionally lacks any init source (used to exercise the
        # projection guard).
        doc["init"] = {"behavior": init_behavior}
    return doc


def _fixture_repo(tmp_path: Path, docs: dict[str, dict]) -> Path:
    """Build a fixture repository with the given ``{kernel_id: doc}`` mapping.

    Each kernel is written to ``docs/kernels/R5/<kernel_id>.yaml`` and
    indexed with its actual SHA-256.
    """

    root = tmp_path / "repo"
    root.mkdir()
    _copy_schema(root)
    files: dict[str, dict] = {}
    for kid, doc in docs.items():
        ring = doc.get("ring", "R5")
        rel = f"docs/kernels/{ring}/{kid}.yaml"
        path = root / rel
        _write_yaml(path, doc)
        files[rel] = {
            "retrieval": "on_demand",
            "role": "kernel",
            "sha256": _sha(path),
            "tags": ["kernels"],
        }
    (root / "AGENT_RETRIEVAL_INDEX.yaml").write_text(
        yaml.safe_dump({"canonical_contract": "TransportPacket", "files": files}, sort_keys=False),
        encoding="utf-8",
    )
    return root


def _custom_resolver(
    tmp_path: Path, kernels: dict[str, dict], profile_map: dict[str, tuple[str, ...]] | None = None
) -> KernelResolver:
    root = _fixture_repo(tmp_path, kernels)
    registry = KernelRegistry.load(root)
    resolver = KernelResolver(registry)
    if profile_map is not None:
        resolver_mod.PROFILE_KERNELS.clear()
        resolver_mod.PROFILE_KERNELS.update(profile_map)
    return resolver


# ---------------------------------------------------------------------------
# BUILD happy path
# ---------------------------------------------------------------------------


def test_build_resolves_canonical_kernel_on_real_repo() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    registry = KernelRegistry.load(repo_root)
    resolver = KernelResolver(registry)
    request = KernelResolutionRequest(
        profile="BUILD",
        consumer="Cursor-Governance/PE",
        objective="ship slice 1",
        trust_level="L3",
        max_overload_weight=6.0,
    )
    resolution = resolver.resolve(request)
    ids = [k.kernel_id for k in resolution.kernels]
    # Dependencies must precede dependents (execution contract §18).
    assert ids == ["l9_coding_kernel.v1", "l9_build_kernel.v1"]
    assert resolution.total_overload_weight == pytest.approx(3.5)
    assert len(resolution.provenance) == 2
    assert all(p.indexed_sha256 == p.verified_sha256 for p in resolution.provenance)
    # Tier-1 projection carries hard_bans; no full doctrine dump.
    assert "hard_bans" in resolution.normative_context["kernels"][0]


# ---------------------------------------------------------------------------
# Trust enforcement
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("trust", ["L0", "L1", "L2"])
def test_build_insufficient_trust_fails(trust: str, tmp_path: Path) -> None:
    resolver = _custom_resolver(
        tmp_path,
        {
            "l9_build_kernel.v1": _kernel("l9_build_kernel.v1", requires=[]),
            "l9_coding_kernel.v1": _kernel("l9_coding_kernel.v1"),
        },
    )
    with pytest.raises(KernelTrustInsufficientError) as ei:
        resolver.resolve(
            KernelResolutionRequest(
                "BUILD",
                "PE",
                "x",
                trust,
                10.0,
            )
        )
    assert ei.value.code == "KERNEL_TRUST_INSUFFICIENT"


def test_build_sufficient_trust_succeeds(tmp_path: Path) -> None:
    resolver = _custom_resolver(
        tmp_path,
        {"l9_build_kernel.v1": _kernel("l9_build_kernel.v1", requires=[])},
    )
    resolution = resolver.resolve(
        KernelResolutionRequest(
            "BUILD",
            "PE",
            "x",
            "L3",
            10.0,
        )
    )
    assert resolution.resolution_digest


# ---------------------------------------------------------------------------
# Dependency resolution
# ---------------------------------------------------------------------------


def test_required_dependency_resolves(tmp_path: Path) -> None:
    resolver = _custom_resolver(
        tmp_path,
        {
            "l9_build_kernel.v1": _kernel("l9_build_kernel.v1", requires=["dep.v1"]),
            "dep.v1": _kernel("dep.v1", weight=0.5),
        },
    )
    resolution = resolver.resolve(
        KernelResolutionRequest(
            "BUILD",
            "PE",
            "x",
            "L3",
            10.0,
        )
    )
    ids = [k.kernel_id for k in resolution.kernels]
    assert ids == ["dep.v1", "l9_build_kernel.v1"]


def test_missing_dependency_fails(tmp_path: Path) -> None:
    resolver = _custom_resolver(
        tmp_path,
        {"l9_build_kernel.v1": _kernel("l9_build_kernel.v1", requires=["ghost.v1"])},
    )
    with pytest.raises(KernelDependencyMissingError) as ei:
        resolver.resolve(
            KernelResolutionRequest(
                "BUILD",
                "PE",
                "x",
                "L3",
                10.0,
            )
        )
    assert ei.value.code == "KERNEL_DEPENDENCY_MISSING"


def test_dependency_cycle_fails(tmp_path: Path) -> None:
    resolver = _custom_resolver(
        tmp_path,
        {"a.v1": _kernel("a.v1", requires=["b.v1"]), "b.v1": _kernel("b.v1", requires=["a.v1"])},
        profile_map={"BUILD": ("a.v1",)},
    )
    with pytest.raises(KernelDependencyCycleError) as ei:
        resolver.resolve(
            KernelResolutionRequest(
                "BUILD",
                "PE",
                "x",
                "L3",
                10.0,
            )
        )
    assert ei.value.code == "KERNEL_DEPENDENCY_CYCLE"


# ---------------------------------------------------------------------------
# Lifecycle status
# ---------------------------------------------------------------------------


def test_deprecated_kernel_fails(tmp_path: Path) -> None:
    resolver = _custom_resolver(
        tmp_path,
        {"l9_build_kernel.v1": _kernel("l9_build_kernel.v1", status="deprecated")},
    )
    with pytest.raises(KernelDeprecatedError) as ei:
        resolver.resolve(
            KernelResolutionRequest(
                "BUILD",
                "PE",
                "x",
                "L3",
                10.0,
            )
        )
    assert ei.value.code == "KERNEL_DEPRECATED"


def test_experimental_kernel_blocked_without_optin(tmp_path: Path) -> None:
    resolver = _custom_resolver(
        tmp_path,
        {"l9_build_kernel.v1": _kernel("l9_build_kernel.v1", status="experimental")},
    )
    with pytest.raises(KernelExperimentalNotAllowedError):
        resolver.resolve(
            KernelResolutionRequest(
                "BUILD",
                "PE",
                "x",
                "L3",
                10.0,
            )
        )
    # And permitted when explicit opt-in is set.
    resolver.resolve(
        KernelResolutionRequest(
            "BUILD",
            "PE",
            "x",
            "L3",
            10.0,
            allow_experimental=True,
        )
    )


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------


def test_overload_budget_totals_correctly(tmp_path: Path) -> None:
    resolver = _custom_resolver(
        tmp_path,
        {
            "l9_build_kernel.v1": _kernel(
                "l9_build_kernel.v1", weight=1.5, requires=["l9_coding_kernel.v1"]
            ),
            "l9_coding_kernel.v1": _kernel("l9_coding_kernel.v1", weight=2.0),
        },
    )
    resolution = resolver.resolve(
        KernelResolutionRequest(
            "BUILD",
            "PE",
            "x",
            "L3",
            10.0,
        )
    )
    assert resolution.total_overload_weight == pytest.approx(3.5)


def test_overload_budget_exceeded_fails(tmp_path: Path) -> None:
    resolver = _custom_resolver(
        tmp_path,
        {
            "l9_build_kernel.v1": _kernel(
                "l9_build_kernel.v1", weight=1.5, requires=["l9_coding_kernel.v1"]
            ),
            "l9_coding_kernel.v1": _kernel("l9_coding_kernel.v1", weight=2.0),
        },
    )
    with pytest.raises(KernelBudgetExceededError) as ei:
        resolver.resolve(
            KernelResolutionRequest(
                "BUILD",
                "PE",
                "x",
                "L3",
                1.0,
            )
        )
    assert ei.value.code == "KERNEL_BUDGET_EXCEEDED"


# ---------------------------------------------------------------------------
# Profiles / requests
# ---------------------------------------------------------------------------


def test_unknown_profile_fails() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    registry = KernelRegistry.load(repo_root)
    resolver = KernelResolver(registry)
    with pytest.raises(KernelProfileUnknownError) as ei:
        resolver.resolve(
            KernelResolutionRequest(
                "WHATEVER",
                "PE",
                "x",
                "L3",
                6.0,
            )
        )
    assert ei.value.code == "KERNEL_PROFILE_UNKNOWN"


def test_requested_kernel_ids_rejected_in_slice_1() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    registry = KernelRegistry.load(repo_root)
    resolver = KernelResolver(registry)
    with pytest.raises(KernelRequestInvalidError):
        resolver.resolve(
            KernelResolutionRequest(
                "BUILD",
                "PE",
                "x",
                "L3",
                6.0,
                requested_kernel_ids=("some.v1",),
            )
        )


def test_invalid_trust_level_rejected() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    registry = KernelRegistry.load(repo_root)
    resolver = KernelResolver(registry)
    with pytest.raises(KernelRequestInvalidError):
        resolver.resolve(
            KernelResolutionRequest(
                "BUILD",
                "PE",
                "x",
                "L9",
                6.0,
            )
        )


def test_schema_invalid_kernel_rejected(tmp_path: Path) -> None:
    bad = _kernel("l9_build_kernel.v1")
    bad.pop("version")
    resolver = _custom_resolver(tmp_path, {"l9_build_kernel.v1": bad})
    with pytest.raises(KernelSchemaInvalidError):
        resolver.resolve(
            KernelResolutionRequest(
                "BUILD",
                "PE",
                "x",
                "L3",
                10.0,
            )
        )
