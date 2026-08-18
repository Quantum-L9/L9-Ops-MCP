"""Tier-1 projection semantics + MCP envelope failure-closed tests.

Covers the two blockers identified in review of PR #20:

1. **Tier-1 projection must emit real ``init.behavior``** (doctrine §6),
   not a documentation surrogate (``purpose``). Contract §21 mandates
   ``init.behavior + hard_bans + identity/provenance``; Slice 1's original
   projection substituted ``purpose`` because Markdown kernels don't
   declare a structured ``init.behavior`` mapping. The fix captures the
   Markdown ``## TIER 1`` body verbatim and emits it as the mechanical
   equivalent, and refuses selection of any kernel with no init source.

2. **The MCP boundary must always return the stable error envelope**
   (contract §33). Malformed inputs (non-coercible types, NaN, ±Inf)
   previously escaped as raw Python tracebacks. The fix coerces inside
   the try block and maps ``TypeError``/``ValueError``/``FileNotFoundError``
   to ``KERNEL_REQUEST_INVALID`` / ``KERNEL_NOT_FOUND``.

3. **Trust provenance** — the response now carries ``trust_level`` at
   the top level so PE consumers can persist it in Program Lock without
   digging into ``normalized_request``.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

try:
    from mcp.server.fastmcp import FastMCP  # noqa: F401
except ImportError:
    pytest.skip("mcp<2.0 FastMCP surface required", allow_module_level=True)

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def _configure_repo_root():
    os.environ["L9_OPS_MCP_REPO_ROOT"] = str(REPO_ROOT)
    yield
    os.environ.pop("L9_OPS_MCP_REPO_ROOT", None)


@pytest.fixture()
def server_module():
    from l9_ops_mcp import server as srv

    srv._KERNEL_REGISTRY = None
    srv._KERNEL_RESOLVER = None
    return srv


# ---------------------------------------------------------------------------
# Tier-1 projection semantics
# ---------------------------------------------------------------------------


def test_tier1_projection_emits_init_behavior_not_purpose_for_markdown_kernels(server_module):
    """BUILD closure is two Markdown kernels; the projection must emit the
    Tier-1 block body, labelled ``tier1_block``, not the ``purpose`` string.
    """

    payload = asyncio.run(
        server_module.kernel_resolve(
            profile="BUILD",
            consumer="Cursor-Governance/PE",
            objective="verify projection",
            trust_level="L3",
            max_overload_weight=6.0,
        )
    )
    assert payload["status"] == "ok"
    ctx = payload["normative_context"]["kernels"]
    assert len(ctx) == 2

    for entry in ctx:
        # New normative fields present.
        assert "init_behavior" in entry
        assert "init_behavior_source" in entry
        # For BUILD closure both are Markdown kernels, so the mechanical
        # source is ``tier1_block``.
        assert entry["init_behavior_source"] == "tier1_block"
        # The init_behavior body must be non-trivial and must include the
        # canonical Tier-1 capability declaration marker.
        assert len(entry["init_behavior"]) > 200
        assert "**capability**" in entry["init_behavior"]
        # And it must NOT be the short purpose string.
        assert entry["init_behavior"] != entry["purpose"]


def test_tier1_projection_uses_structured_init_behavior_for_yaml_kernels():
    """A resolver that selects a YAML kernel (e.g. context_budget_kernel.v1)
    must project its ``init.behavior`` mapping value, labelled
    ``init.behavior``.
    """

    from l9_ops_mcp import kernel_resolver as resolver_mod
    from l9_ops_mcp.kernel_registry import KernelRegistry
    from l9_ops_mcp.kernel_models import KernelResolutionRequest
    from l9_ops_mcp.kernel_resolver import KernelResolver

    # Register a one-off profile whose seed is a YAML kernel with a
    # structured init.behavior block.
    original = dict(resolver_mod.PROFILE_KERNELS)
    resolver_mod.PROFILE_KERNELS.clear()
    resolver_mod.PROFILE_KERNELS.update({"CONTEXT_BUDGET": ("context_budget_kernel.v1",)})
    try:
        # This YAML kernel requires trust_ladder + memory_admission.
        registry = KernelRegistry.load(REPO_ROOT)
        resolver = KernelResolver(registry)
        resolution = resolver.resolve(
            KernelResolutionRequest(
                profile="CONTEXT_BUDGET",
                consumer="test",
                objective="yaml init.behavior projection",
                trust_level="L3",
                max_overload_weight=10.0,
            )
        )
    finally:
        resolver_mod.PROFILE_KERNELS.clear()
        resolver_mod.PROFILE_KERNELS.update(original)

    for k in resolution.normative_context["kernels"]:
        assert k["init_behavior_source"] == "init.behavior", (
            f"YAML kernel {k['kernel_id']} should project structured "
            f"init.behavior, got source={k['init_behavior_source']}"
        )
        assert k["init_behavior"], f"empty init_behavior for {k['kernel_id']}"


def test_kernel_with_no_init_source_is_refused_at_selection(tmp_path, monkeypatch):
    """A kernel that lacks both ``init.behavior`` and a Markdown Tier-1
    block must not reach the Tier-1 projection. The lifecycle gate refuses
    it with ``KERNEL_SCHEMA_INVALID``.
    """

    import hashlib

    import yaml

    from l9_ops_mcp import kernel_resolver as resolver_mod
    from l9_ops_mcp.kernel_models import (
        KernelResolutionRequest,
        KernelSchemaInvalidError,
    )
    from l9_ops_mcp.kernel_registry import KernelRegistry
    from l9_ops_mcp.kernel_resolver import KernelResolver

    # Build a synthetic canonical kernel with no init.behavior.
    root = tmp_path / "repo"
    root.mkdir()
    schema_src = REPO_ROOT / "schemas" / "kernel.canonical.schema.json"
    (root / "schemas").mkdir()
    (root / "schemas" / "kernel.canonical.schema.json").write_text(
        schema_src.read_text(encoding="utf-8"), encoding="utf-8"
    )
    kernel_doc = {
        "kernel_id": "no_init.v1",
        "version": "1.0.0",
        "ring": "R5",
        "category": "developer_support",
        "title": "kernel without init.behavior",
        "purpose": "does not project as normative init",
        "activation_phase": "on_demand",
        "status": "active",
        "overload_weight": 1.0,
        "hard_bans": ["MUST NOT be projected"],
        "fail_closed": True,
        # Deliberately no ``init`` mapping.
    }
    kernel_rel = "docs/kernels/R5/no_init.v1.yaml"
    kernel_path = root / kernel_rel
    kernel_path.parent.mkdir(parents=True, exist_ok=True)
    kernel_path.write_text(yaml.safe_dump(kernel_doc, sort_keys=False), encoding="utf-8")
    idx_doc = {
        "canonical_contract": "TransportPacket",
        "files": {
            kernel_rel: {
                "retrieval": "on_demand",
                "role": "kernel",
                "sha256": hashlib.sha256(kernel_path.read_bytes()).hexdigest(),
                "tags": ["kernels"],
            }
        },
    }
    (root / "AGENT_RETRIEVAL_INDEX.yaml").write_text(
        yaml.safe_dump(idx_doc, sort_keys=False), encoding="utf-8"
    )

    monkeypatch.setattr(resolver_mod, "PROFILE_KERNELS", {"NO_INIT": ("no_init.v1",)})
    registry = KernelRegistry.load(root)
    definition = registry.get("no_init.v1")
    assert definition.init_behavior_source == "absent"
    resolver = KernelResolver(registry)
    with pytest.raises(KernelSchemaInvalidError) as ei:
        resolver.resolve(
            KernelResolutionRequest(
                profile="NO_INIT",
                consumer="test",
                objective="should not project",
                trust_level="L3",
                max_overload_weight=10.0,
            )
        )
    assert ei.value.code == "KERNEL_SCHEMA_INVALID"
    assert "no normative init.behavior" in ei.value.message


def test_tier1_projection_still_includes_hard_bans_and_purpose(server_module):
    """The projection expansion must be additive \u2014 hard_bans and purpose
    remain in the response so existing consumers don't regress.
    """

    payload = asyncio.run(
        server_module.kernel_resolve(
            profile="BUILD",
            consumer="test",
            objective="regression check",
            trust_level="L3",
            max_overload_weight=6.0,
        )
    )
    for k in payload["normative_context"]["kernels"]:
        assert isinstance(k["hard_bans"], list) and k["hard_bans"]
        assert k["purpose"]  # non-empty documentation adjunct
        # Provenance-adjacent identity still present.
        assert k["canonical_path"].startswith("docs/kernels/")
        assert len(k["sha256"]) == 64


# ---------------------------------------------------------------------------
# MCP error envelope closure
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "budget"),
    [
        ("non-coercible string", "not-a-number"),
        ("None", None),
        ("NaN", float("nan")),
        ("+inf", float("inf")),
        ("-inf", float("-inf")),
        ("list", [1, 2, 3]),
        ("dict", {"nope": True}),
    ],
)
def test_malformed_budget_returns_stable_error_envelope(server_module, label, budget):
    """Every malformed budget input must produce ``KERNEL_REQUEST_INVALID``.

    Slice 1 originally escaped as a raw Python traceback for
    non-coercible strings and NaN. The fix coerces inside the try and
    rejects NaN/Inf explicitly.
    """

    result = asyncio.run(
        server_module.kernel_resolve(
            profile="BUILD",
            consumer="test",
            objective=f"malformed {label}",
            trust_level="L3",
            max_overload_weight=budget,  # type: ignore[arg-type]
        )
    )
    assert result["status"] == "error"
    assert result["code"] == "KERNEL_REQUEST_INVALID"
    # ``trust_level`` is only surfaced on the success envelope.
    assert "trust_level" not in result or result.get("trust_level") is None


def test_numeric_string_budget_is_accepted(server_module):
    """Coercion accepts ``\"6.0\"`` since ``float(\"6.0\")`` is well-defined
    and safe; this is a compatibility affordance, not a design choice.
    """

    result = asyncio.run(
        server_module.kernel_resolve(
            profile="BUILD",
            consumer="test",
            objective="numeric string budget",
            trust_level="L3",
            max_overload_weight="6.0",  # type: ignore[arg-type]
        )
    )
    assert result["status"] == "ok"


def test_registry_load_failure_is_mapped_to_kernel_not_found(monkeypatch, tmp_path):
    """If the registry raises ``FileNotFoundError`` (missing index, missing
    schema, missing artifact), the MCP boundary must still return the
    stable error envelope.
    """

    from l9_ops_mcp import server as srv

    # Point at a tmp directory with no retrieval index.
    monkeypatch.setenv("L9_OPS_MCP_REPO_ROOT", str(tmp_path))
    srv._KERNEL_REGISTRY = None
    srv._KERNEL_RESOLVER = None
    result = asyncio.run(
        srv.kernel_resolve(
            profile="BUILD",
            consumer="test",
            objective="missing repo state",
            trust_level="L3",
            max_overload_weight=6.0,
        )
    )
    assert result["status"] == "error"
    # KernelRegistry.load raises KernelNotFoundError when repo_root does
    # not exist; if it existed but had no index, it would raise
    # KernelIndexEntryMissingError. Both are KernelAuthorityError subclasses
    # and both funnel through the same envelope path.
    assert result["code"] in {
        "KERNEL_NOT_FOUND",
        "KERNEL_INDEX_ENTRY_MISSING",
    }
    # Ensure the cache is reset for later tests.
    srv._KERNEL_REGISTRY = None
    srv._KERNEL_RESOLVER = None


# ---------------------------------------------------------------------------
# Trust-level provenance in the response
# ---------------------------------------------------------------------------


def test_response_carries_top_level_trust_level(server_module):
    """PE consumers can persist the gating trust level directly from the
    response without re-reading ``normalized_request``.
    """

    payload = asyncio.run(
        server_module.kernel_resolve(
            profile="BUILD",
            consumer="test",
            objective="trust provenance",
            trust_level="L3",
            max_overload_weight=6.0,
        )
    )
    assert payload["status"] == "ok"
    assert payload["trust_level"] == "L3"
    # And it must match the value already embedded in normalized_request
    # (which itself is part of the resolution digest).
    assert payload["normalized_request"]["trust_level"] == "L3"


# ---------------------------------------------------------------------------
# Cache-invalidation opt-in
# ---------------------------------------------------------------------------


def test_strict_integrity_env_forces_reverify(monkeypatch, server_module):
    """Setting ``L9_KERNEL_STRICT_INTEGRITY=1`` re-verifies every canonical
    kernel's sha256 on every resolve. If the on-disk bytes drift the
    resolver refuses with ``KERNEL_DIGEST_MISMATCH``.
    """

    # First: warm the cache.
    monkeypatch.delenv("L9_KERNEL_STRICT_INTEGRITY", raising=False)
    r1 = asyncio.run(
        server_module.kernel_resolve(
            profile="BUILD",
            consumer="test",
            objective="warm",
            trust_level="L3",
            max_overload_weight=6.0,
        )
    )
    assert r1["status"] == "ok"

    # Now poison the cached registry's record for one kernel and turn
    # strict mode on. The re-verify must catch the drift.
    from dataclasses import replace

    reg = server_module._KERNEL_REGISTRY
    assert reg is not None
    victim = reg.get("l9_build_kernel.v1")
    tampered = replace(victim, sha256="0" * 64)
    reg._kernels["l9_build_kernel.v1"] = tampered  # type: ignore[attr-defined]

    monkeypatch.setenv("L9_KERNEL_STRICT_INTEGRITY", "1")
    r2 = asyncio.run(
        server_module.kernel_resolve(
            profile="BUILD",
            consumer="test",
            objective="strict mode",
            trust_level="L3",
            max_overload_weight=6.0,
        )
    )
    assert r2["status"] == "error"
    assert r2["code"] == "KERNEL_DIGEST_MISMATCH"

    # Reset for later tests.
    server_module._KERNEL_REGISTRY = None
    server_module._KERNEL_RESOLVER = None
