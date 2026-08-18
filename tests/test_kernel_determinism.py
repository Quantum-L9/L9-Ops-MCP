"""Determinism, digest sensitivity, and canonical JSON tests.

Covers execution contract §25 (canonical serialization), §26 (deterministic
replay across separate processes), §27 (digest sensitivity to authority
changes), §43 (digest tests — replay, independent instances, authority change,
order invariance).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from l9_ops_mcp.kernel_models import KernelResolutionRequest
from l9_ops_mcp.kernel_registry import KernelRegistry
from l9_ops_mcp.kernel_resolver import KernelResolver, canonical_json


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def resolver() -> KernelResolver:
    return KernelResolver(KernelRegistry.load(REPO_ROOT))


def _build_request(**overrides) -> KernelResolutionRequest:
    defaults = dict(
        profile="BUILD",
        consumer="Cursor-Governance/PE",
        objective="ship slice 1",
        trust_level="L3",
        max_overload_weight=6.0,
    )
    defaults.update(overrides)
    return KernelResolutionRequest(**defaults)


def test_same_request_same_digest(resolver) -> None:
    req = _build_request()
    d1 = resolver.resolve(req).resolution_digest
    d2 = resolver.resolve(req).resolution_digest
    assert d1 == d2


def test_independent_resolver_instances_yield_same_digest() -> None:
    reg_a = KernelRegistry.load(REPO_ROOT)
    reg_b = KernelRegistry.load(REPO_ROOT)
    res_a = KernelResolver(reg_a).resolve(_build_request())
    res_b = KernelResolver(reg_b).resolve(_build_request())
    assert res_a.resolution_digest == res_b.resolution_digest


def test_subprocess_replay_yields_same_digest() -> None:
    """Execution contract §26 — deterministic replay across separate processes."""

    script = (
        "import sys; sys.path.insert(0, 'src'); "
        "from l9_ops_mcp.kernel_registry import KernelRegistry; "
        "from l9_ops_mcp.kernel_resolver import KernelResolver; "
        "from l9_ops_mcp.kernel_models import KernelResolutionRequest; "
        "r = KernelResolver(KernelRegistry.load('.')); "
        "req = KernelResolutionRequest('BUILD','Cursor-Governance/PE','ship slice 1','L3',6.0); "
        "print(r.resolve(req).resolution_digest)"
    )
    a = subprocess.run(
        [sys.executable, "-c", script], cwd=REPO_ROOT,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    b = subprocess.run(
        [sys.executable, "-c", script], cwd=REPO_ROOT,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert a == b
    assert len(a) == 64  # sha256 hex


def test_digest_sensitivity_to_selected_kernel_hash(resolver, tmp_path, monkeypatch) -> None:
    """Execution contract §27 — changing a selected kernel's verified content
    hash in a fixture must change the resolution identity.
    """

    baseline = resolver.resolve(_build_request()).resolution_digest
    # Rebuild a resolver where the selected kernel's stored sha256 has been
    # tampered with. We do this by mutating the KernelDefinition in the
    # registry snapshot via dataclasses.replace.
    from dataclasses import replace

    reg = KernelRegistry.load(REPO_ROOT)
    original = reg.get("l9_build_kernel.v1")
    mutated = replace(original, sha256="f" * 64)
    reg._kernels["l9_build_kernel.v1"] = mutated  # type: ignore[attr-defined]
    perturbed = KernelResolver(reg).resolve(_build_request()).resolution_digest
    assert perturbed != baseline


def test_digest_sensitivity_to_normative_content(resolver) -> None:
    """Contract §27 — mutating Tier-1 hard_bans in the registry snapshot
    must alter the digest (proves digest reads normative content, not just
    identity).
    """

    baseline = resolver.resolve(_build_request()).resolution_digest
    from dataclasses import replace

    reg = KernelRegistry.load(REPO_ROOT)
    original = reg.get("l9_build_kernel.v1")
    mutated = replace(
        original,
        hard_bans=original.hard_bans + ("MUST NOT introduce novel violations",),
    )
    reg._kernels["l9_build_kernel.v1"] = mutated  # type: ignore[attr-defined]
    perturbed = KernelResolver(reg).resolve(_build_request()).resolution_digest
    # Normative content flows into Tier-1 projection, which flows into the
    # digested payload, so this MUST differ from baseline.
    assert perturbed != baseline


def test_selected_kernels_stable_across_objective_variation(resolver) -> None:
    """Contract §34 — objective must not semantically alter BUILD selection.

    Objective flows into ``normalized_request`` and therefore into the digest
    for provenance, so digests MAY legitimately differ across objective text.
    The invariant to prove here is that the SELECTED KERNEL SET is stable.
    """

    res_a = resolver.resolve(_build_request(objective="AAA"))
    res_b = resolver.resolve(_build_request(objective="BBB"))
    assert [k.kernel_id for k in res_a.kernels] == [k.kernel_id for k in res_b.kernels]


def test_canonical_json_is_stable_across_key_order() -> None:
    """Contract §43 — order invariance for logically equivalent input maps."""

    a = canonical_json({"b": 1, "a": [1, 2, 3]})
    b = canonical_json({"a": [1, 2, 3], "b": 1})
    assert a == b
    parsed = json.loads(a.decode("utf-8"))
    assert list(parsed) == sorted(parsed)


def test_canonical_json_refuses_nan() -> None:
    with pytest.raises(ValueError):
        canonical_json({"x": float("nan")})


def test_canonical_json_bytes_are_utf8_and_compact() -> None:
    payload = canonical_json({"greeting": "hællo"})
    assert isinstance(payload, bytes)
    parsed = json.loads(payload.decode("utf-8"))
    assert parsed == {"greeting": "hællo"}
    # Compact separators — no whitespace.
    assert b" " not in payload
