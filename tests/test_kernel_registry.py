"""Unit tests for :mod:`l9_ops_mcp.kernel_registry` (execution contract §40).

These tests do NOT read any live external service. They exercise the registry
against synthetic fixture repositories built in ``tmp_path`` so every
adversarial branch is deterministic.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from l9_ops_mcp.kernel_models import (
    KernelDigestMismatchError,
    KernelDuplicateIdError,
    KernelIndexEntryMissingError,
    KernelNotFoundError,
)
from l9_ops_mcp.kernel_registry import KernelRegistry


CANONICAL_SCHEMA_SRC = (
    Path(__file__).resolve().parents[1] / "schemas" / "kernel.canonical.schema.json"
)


def _write_yaml_kernel(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def _write_index(root: Path, files: dict[str, dict]) -> None:
    doc = {"canonical_contract": "TransportPacket", "files": files}
    (root / "AGENT_RETRIEVAL_INDEX.yaml").write_text(
        yaml.safe_dump(doc, sort_keys=False), encoding="utf-8"
    )


def _copy_schema(root: Path) -> None:
    dest = root / "schemas" / "kernel.canonical.schema.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(CANONICAL_SCHEMA_SRC.read_text(encoding="utf-8"), encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _minimal_valid_kernel(
    kernel_id: str,
    ring: str = "R5",
    weight: float = 1.0,
    requires: list[str] | None = None,
    status: str = "active",
) -> dict:
    return {
        "kernel_id": kernel_id,
        "version": "1.0.0",
        "ring": ring,
        "category": "developer_support",
        "title": f"{kernel_id} title",
        "purpose": "Trigger WHAT / WHEN / WHY three-sentence purpose statement.",
        "activation_phase": "on_demand",
        "status": status,
        "overload_weight": weight,
        "hard_bans": [f"MUST NOT violate {kernel_id}"],
        "fail_closed": True,
        "requires": requires or [],
    }


def _build_fixture(
    tmp_path: Path,
    kernels: dict[str, dict],
    *,
    subdir: str = "R5",
    corrupt_hash: str | None = None,
    omit_from_index: str | None = None,
    duplicate_of: tuple[str, str] | None = None,
) -> Path:
    """Build a synthetic repository under tmp_path and return its root."""

    root = tmp_path / "repo"
    root.mkdir()
    _copy_schema(root)

    files_index: dict[str, dict] = {}
    for name, doc in kernels.items():
        rel = f"docs/kernels/{subdir}/{name}"
        path = root / rel
        _write_yaml_kernel(path, doc)
        files_index[rel] = {
            "retrieval": "on_demand",
            "role": "kernel",
            "sha256": _sha(path),
            "tags": ["kernels"],
        }
    # Duplicate: write a second file with identical kernel_id under a different
    # filename inside the canonical tree.
    if duplicate_of is not None:
        original_name, dup_name = duplicate_of
        dup_rel = f"docs/kernels/{subdir}/{dup_name}"
        dup_path = root / dup_rel
        _write_yaml_kernel(dup_path, kernels[original_name])
        files_index[dup_rel] = {
            "retrieval": "on_demand",
            "role": "kernel",
            "sha256": _sha(dup_path),
            "tags": ["kernels"],
        }
    if corrupt_hash is not None:
        files_index[corrupt_hash]["sha256"] = "0" * 64
    if omit_from_index is not None:
        # Physically create a kernel file but do not tag it in the index; it
        # must therefore not be discovered by the registry.
        rel = omit_from_index
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("kernel_id: hidden.v1\n", encoding="utf-8")
    _write_index(root, files_index)
    return root


# ---------------------------------------------------------------------------
# Contract §40 — valid indexed kernel loads
# ---------------------------------------------------------------------------


def test_valid_indexed_kernel_loads(tmp_path: Path) -> None:
    root = _build_fixture(
        tmp_path,
        {"alpha_kernel.v1.yaml": _minimal_valid_kernel("alpha_kernel.v1")},
    )
    registry = KernelRegistry.load(root)
    kernel = registry.get("alpha_kernel.v1")
    assert kernel.schema_valid is True
    assert kernel.canonical_path == "docs/kernels/R5/alpha_kernel.v1.yaml"
    assert kernel.hard_bans == ("MUST NOT violate alpha_kernel.v1",)
    assert registry.list_active() == [kernel]


def test_untagged_kernel_file_is_not_discovered(tmp_path: Path) -> None:
    # Contract §12: registry must not pull evaluation fixtures or arbitrary
    # YAML/Markdown files. Only tagged docs/kernels/** entries qualify.
    root = _build_fixture(
        tmp_path,
        {"alpha_kernel.v1.yaml": _minimal_valid_kernel("alpha_kernel.v1")},
        omit_from_index="docs/kernels/R5/hidden_kernel.v1.yaml",
    )
    registry = KernelRegistry.load(root)
    assert not registry.has("hidden.v1")


# ---------------------------------------------------------------------------
# Contract §40 — missing index entry fails / digest mismatch fails closed
# ---------------------------------------------------------------------------


def test_digest_mismatch_fails_closed(tmp_path: Path) -> None:
    kernels = {"alpha_kernel.v1.yaml": _minimal_valid_kernel("alpha_kernel.v1")}
    root = _build_fixture(
        tmp_path,
        kernels,
        corrupt_hash="docs/kernels/R5/alpha_kernel.v1.yaml",
    )
    with pytest.raises(KernelDigestMismatchError):
        KernelRegistry.load(root)


def test_missing_sha_in_index_fails(tmp_path: Path) -> None:
    root = _build_fixture(
        tmp_path,
        {"alpha_kernel.v1.yaml": _minimal_valid_kernel("alpha_kernel.v1")},
    )
    # Remove the sha256 line from the index.
    idx_path = root / "AGENT_RETRIEVAL_INDEX.yaml"
    idx = yaml.safe_load(idx_path.read_text(encoding="utf-8"))
    idx["files"]["docs/kernels/R5/alpha_kernel.v1.yaml"].pop("sha256")
    idx_path.write_text(yaml.safe_dump(idx, sort_keys=False), encoding="utf-8")
    with pytest.raises(KernelIndexEntryMissingError):
        KernelRegistry.load(root)


def test_indexed_path_missing_on_disk(tmp_path: Path) -> None:
    root = _build_fixture(
        tmp_path,
        {"alpha_kernel.v1.yaml": _minimal_valid_kernel("alpha_kernel.v1")},
    )
    # Delete the artifact but keep the index entry.
    (root / "docs/kernels/R5/alpha_kernel.v1.yaml").unlink()
    with pytest.raises(KernelNotFoundError):
        KernelRegistry.load(root)


# ---------------------------------------------------------------------------
# Contract §40 — schema validation
# ---------------------------------------------------------------------------


def test_malformed_kernel_is_registered_but_marked_schema_invalid(tmp_path: Path) -> None:
    bad = _minimal_valid_kernel("bad_kernel.v1")
    bad.pop("version")
    bad.pop("title")
    root = _build_fixture(tmp_path, {"bad_kernel.v1.yaml": bad})
    registry = KernelRegistry.load(root)
    # Registry retains parseable content but flags schema violations so the
    # resolver refuses the kernel at selection time (execution contract §33).
    k = registry.get("bad_kernel.v1")
    assert k.schema_valid is False
    assert any("version" in msg for msg in k.schema_errors)


def test_unknown_kernel_id_fails(tmp_path: Path) -> None:
    root = _build_fixture(
        tmp_path, {"alpha_kernel.v1.yaml": _minimal_valid_kernel("alpha_kernel.v1")}
    )
    registry = KernelRegistry.load(root)
    with pytest.raises(KernelNotFoundError):
        registry.get("does_not_exist.v1")


# ---------------------------------------------------------------------------
# Contract §40 — duplicate canonical id fails
# ---------------------------------------------------------------------------


def test_duplicate_kernel_id_fails(tmp_path: Path) -> None:
    kernels = {"alpha_kernel.v1.yaml": _minimal_valid_kernel("alpha_kernel.v1")}
    root = _build_fixture(
        tmp_path,
        kernels,
        duplicate_of=("alpha_kernel.v1.yaml", "alpha_dup.yaml"),
    )
    with pytest.raises(KernelDuplicateIdError):
        KernelRegistry.load(root)


# ---------------------------------------------------------------------------
# Contract §38 — path escapes rejected
# ---------------------------------------------------------------------------


def test_index_path_outside_repo_root_rejected(tmp_path: Path) -> None:
    root = _build_fixture(
        tmp_path, {"alpha_kernel.v1.yaml": _minimal_valid_kernel("alpha_kernel.v1")}
    )
    idx_path = root / "AGENT_RETRIEVAL_INDEX.yaml"
    idx = yaml.safe_load(idx_path.read_text(encoding="utf-8"))
    idx["files"]["docs/kernels/R5/../../../outside.yaml"] = {
        "retrieval": "on_demand",
        "role": "kernel",
        "sha256": "0" * 64,
        "tags": ["kernels"],
    }
    idx_path.write_text(yaml.safe_dump(idx, sort_keys=False), encoding="utf-8")
    with pytest.raises(KernelNotFoundError):
        KernelRegistry.load(root)


# ---------------------------------------------------------------------------
# Contract §46 — production canonical repo integrity
# ---------------------------------------------------------------------------


def test_real_repo_kernels_load_and_bulid_closure_is_valid() -> None:
    """The real docs/kernels/ tree must load cleanly. Every kernel in the
    BUILD-profile dependency closure must be schema-valid.
    """
    repo_root = Path(__file__).resolve().parents[1]
    registry = KernelRegistry.load(repo_root)
    build = registry.get("l9_build_kernel.v1")
    coding = registry.get("l9_coding_kernel.v1")
    assert build.schema_valid, build.schema_errors
    assert coding.schema_valid, coding.schema_errors
    # All kernels registered by the retrieval index MUST be discoverable.
    all_ids = {k.kernel_id for k in registry.all()}
    assert "l9_build_kernel.v1" in all_ids
    assert "trust_ladder_kernel.v1" in all_ids
