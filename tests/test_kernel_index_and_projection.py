"""Retrieval-index drift + progressive-disclosure tests.

Contract §42 (progressive disclosure), §46 (schema validation over the real
canonical kernel corpus), §47 (retrieval index drift).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from l9_ops_mcp.kernel_registry import (
    CANONICAL_KERNEL_ROOT,
    CANONICAL_KERNEL_TAG,
    KernelRegistry,
    RETRIEVAL_INDEX_FILENAME,
)
from l9_ops_mcp.kernel_resolver import KernelResolver
from l9_ops_mcp.kernel_models import KernelResolutionRequest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_index() -> dict:
    return yaml.safe_load((REPO_ROOT / RETRIEVAL_INDEX_FILENAME).read_text(encoding="utf-8"))


def test_every_docs_kernels_file_is_indexed() -> None:
    """Every artifact in docs/kernels/** must appear in the retrieval index
    tagged as ``kernels``. Contract §47 — detect drift, do not repair it.
    """
    idx = _load_index()
    files = idx["files"]
    on_disk = sorted(
        str(p.relative_to(REPO_ROOT)).replace("\\", "/")
        for p in (REPO_ROOT / "docs/kernels").rglob("*")
        if p.is_file() and p.suffix in {".yaml", ".yml", ".md"}
    )
    for rel in on_disk:
        assert rel in files, f"kernel {rel} not in retrieval index"
        tags = files[rel].get("tags") or []
        assert CANONICAL_KERNEL_TAG in tags, f"kernel {rel} not tagged 'kernels'"


def test_every_indexed_kernel_hash_matches_actual_bytes() -> None:
    idx = _load_index()
    for rel, meta in idx["files"].items():
        if not rel.startswith(CANONICAL_KERNEL_ROOT):
            continue
        tags = meta.get("tags") or []
        if CANONICAL_KERNEL_TAG not in tags:
            continue
        expected = meta["sha256"]
        actual = hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()
        assert expected == actual, (
            f"retrieval index sha drift for {rel}: "
            f"indexed={expected[:12]} actual={actual[:12]}"
        )


def test_build_normative_context_is_tier1_bounded() -> None:
    resolver = KernelResolver(KernelRegistry.load(REPO_ROOT))
    resolution = resolver.resolve(KernelResolutionRequest(
        "BUILD", "PE", "x", "L3", 6.0,
    ))
    ctx = resolution.normative_context
    assert set(ctx) == {"kernels"}
    for k in ctx["kernels"]:
        # Must carry identity, purpose, hard_bans, path/hash.
        assert set(k) >= {
            "kernel_id", "version", "ring", "activation_phase", "status",
            "purpose", "hard_bans", "canonical_path", "sha256",
        }
        # Progressive disclosure: no whole-doctrine dump. Purpose must be
        # short (single-sentence Trigger Triad, per doctrine §5).
        assert len(k["purpose"]) < 2000
        # No raw file-body payload smuggled through the projection.
        for banned_field in ("body", "content", "markdown", "full_text"):
            assert banned_field not in k


def test_build_response_does_not_include_unrelated_kernels() -> None:
    resolver = KernelResolver(KernelRegistry.load(REPO_ROOT))
    resolution = resolver.resolve(KernelResolutionRequest(
        "BUILD", "PE", "x", "L3", 6.0,
    ))
    ids = {k.kernel_id for k in resolution.kernels}
    # Only BUILD closure — no accidental soul/preferences/trust_ladder scoops.
    assert ids == {"l9_build_kernel.v1", "l9_coding_kernel.v1"}
