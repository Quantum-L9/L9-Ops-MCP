# --- L9_META ---
# l9_schema: 1
# artifact_type: runtime_module
# component: kernel_authority_registry
# tags: [kernel-authority, registry, integrity, canonical]
# retrieval: on_demand
# status: active
# --- /L9_META ---
"""Deterministic canonical kernel registry (Slice 1).

Responsibilities:

- Discover canonical kernel artifacts from ``AGENT_RETRIEVAL_INDEX.yaml``
  filtered to the canonical kernel location tree (``docs/kernels/**``).
- Parse both YAML and Markdown kernel formats deterministically.
- Verify actual SHA-256 of every discovered artifact against the indexed hash;
  a mismatch is a hard :class:`KernelDigestMismatchError` at load time.
- Validate parsed kernels against ``schemas/kernel.canonical.schema.json``
  and store the result on :class:`KernelDefinition.schema_valid`. Malformed
  kernels remain parseable but cannot be selected by the resolver.
- Detect duplicate ``kernel_id`` across registered artifacts.

This module has no dependency on Graphiti, Neo4j, MCP, an LLM, or the
memory plane. It contains no applicability policy — that lives in
:mod:`kernel_resolver`.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from .kernel_models import (
    KernelDefinition,
    KernelDigestMismatchError,
    KernelDuplicateIdError,
    KernelIndexEntryMissingError,
    KernelNotFoundError,
    KernelSchemaInvalidError,
    VALID_ACTIVATION_PHASE,
    VALID_STATUS,
)

CANONICAL_KERNEL_ROOT = "docs/kernels/"
CANONICAL_KERNEL_TAG = "kernels"
RETRIEVAL_INDEX_FILENAME = "AGENT_RETRIEVAL_INDEX.yaml"
CANONICAL_SCHEMA_PATH = "schemas/kernel.canonical.schema.json"

# Doctrine §2: rings map to canonical activation phases.
RING_ACTIVATION_PHASE: dict[str, str] = {
    "R0": "always",
    "R1": "always",
    "R2": "always",
    "R3": "always",
    "R4": "always",
    "R5": "on_demand",
    "R6": "lazy",
}

_L9_META_HTML_RE = re.compile(
    r"<!--\s*L9_META\s*\n(?P<body>.*?)\n\s*/L9_META\s*-->",
    re.DOTALL,
)
_L9_META_YAML_HEADER_RE = re.compile(
    r"^---\s*\n(?P<body>.*?)\n---\s*\n",
    re.DOTALL,
)
_L9_META_HASH_COMMENT_RE = re.compile(
    r"^#\s*L9_META\s*\n(?P<body>(?:^#.*\n)+?)#\s*/L9_META\s*\n",
    re.DOTALL | re.MULTILINE,
)
_MD_HARD_BANS_RE = re.compile(
    r"\*\*hard_bans\*\*\s*:\s*\n(?P<items>(?:-\s*MUST NOT[^\n]*\n)+)",
)
_MD_INIT_BEHAVIOR_RE = re.compile(
    r"^\s*\*\*capability\*\*\s*:\s*(?P<val>.+?)(?:\n\n|\n\*\*)",
    re.DOTALL | re.MULTILINE,
)
_KERNEL_ID_FROM_FILENAME_RE = re.compile(r"^(?P<id>[a-z][a-z0-9_]*\.v[0-9]+)")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve_within_repo(repo_root: Path, rel: str) -> Path:
    """Return the absolute path for ``rel`` inside ``repo_root``.

    Rejects absolute paths, ``..`` escapes, and symlinks that resolve outside
    the repository. See execution contract §38 (Security properties).
    """

    if Path(rel).is_absolute():
        raise KernelNotFoundError(f"absolute path not permitted: {rel}")
    joined = (repo_root / rel).resolve()
    root_resolved = repo_root.resolve()
    try:
        joined.relative_to(root_resolved)
    except ValueError as exc:
        raise KernelNotFoundError(f"path escapes repository root: {rel}") from exc
    return joined


def _load_canonical_schema(repo_root: Path) -> dict[str, Any]:
    schema_path = _resolve_within_repo(repo_root, CANONICAL_SCHEMA_PATH)
    loaded: dict[str, Any] = json.loads(schema_path.read_text(encoding="utf-8"))
    return loaded


def _parse_yaml_kernel(raw_text: str) -> dict[str, Any]:
    """Deterministically parse a canonical YAML kernel document.

    Strips two possible header forms (the ``# L9_META`` line-comment banner
    and the ``---`` YAML front-matter banner) if present, then loads the
    remainder with :func:`yaml.safe_load` (no arbitrary Python objects).
    """

    body = raw_text
    m_hash = _L9_META_HASH_COMMENT_RE.search(body)
    if m_hash is not None and m_hash.start() == 0:
        body = body[m_hash.end() :]
    m_front = _L9_META_YAML_HEADER_RE.search(body)
    if m_front is not None and m_front.start() == 0:
        body = body[m_front.end() :]
    doc = yaml.safe_load(body)
    if doc is None:
        return {}
    if not isinstance(doc, dict):
        raise KernelNotFoundError("YAML kernel is not a mapping document")
    return doc


def _parse_markdown_kernel(raw_text: str, canonical_path: str) -> dict[str, Any]:
    """Extract structured fields from a Markdown kernel deterministically.

    Sources (mechanical only, per contract §14 and §553):

    - ``L9_META`` HTML comment → YAML metadata block (canonical, ring,
      version, status, requires, overload_weight, tags, ...).
    - Filename → ``kernel_id`` (regex ``^[a-z][a-z0-9_]*\\.v[0-9]+``).
    - ``**hard_bans**:`` list → ``hard_bans`` array.
    - ``**capability**:`` sentence → ``purpose`` fallback when the meta
      block does not provide one.
    - Doctrine §2 ring-to-activation-phase table → ``activation_phase``.

    No semantic guessing; unknown fields are preserved verbatim in
    ``raw_metadata`` for downstream compatibility.
    """

    meta: dict[str, Any] = {}
    m = _L9_META_HTML_RE.search(raw_text)
    if m is not None:
        try:
            loaded = yaml.safe_load(m.group("body"))
        except yaml.YAMLError as exc:
            raise KernelNotFoundError(
                f"malformed L9_META block in {canonical_path}: {exc}"
            ) from exc
        if isinstance(loaded, dict):
            meta.update(loaded)

    # Filename-derived kernel_id (mechanical).
    stem = Path(canonical_path).name
    stem = re.sub(r"\.(md|yaml|yml)$", "", stem)
    id_match = _KERNEL_ID_FROM_FILENAME_RE.match(stem)
    if "kernel_id" not in meta and id_match is not None:
        meta["kernel_id"] = id_match.group("id")

    # Deterministic hard_bans extraction from Tier-1 Markdown body.
    hb = _MD_HARD_BANS_RE.search(raw_text)
    if hb is not None:
        items: list[str] = []
        for line in hb.group("items").splitlines():
            line = line.strip()
            if not line.startswith("-"):
                continue
            text = line.lstrip("- ").strip()
            if text.startswith("MUST NOT"):
                items.append(text)
        if items:
            meta.setdefault("hard_bans", items)

    # Category from layer[-1] (mechanical) when absent.
    layer = meta.get("layer")
    if "category" not in meta and isinstance(layer, list) and layer:
        last = layer[-1]
        if isinstance(last, str):
            meta["category"] = last

    # Title/purpose fallbacks from the capability sentence.
    if "purpose" not in meta:
        cap = _MD_INIT_BEHAVIOR_RE.search(raw_text)
        if cap is not None:
            meta["purpose"] = re.sub(r"\s+", " ", cap.group("val")).strip()
    if "title" not in meta:
        # Use kernel_id as a stable last-resort title.
        title_source = meta.get("kernel_id")
        if isinstance(title_source, str):
            meta["title"] = title_source

    return meta


def _apply_mechanical_derivations(meta: dict[str, Any]) -> None:
    """Fill in doctrine-mechanical fields when the artifact omits them.

    Only mechanical projections from other declared fields are applied here;
    no semantic guessing. See execution contract §14 and §553.
    """

    ring = meta.get("ring")
    if isinstance(ring, str) and "activation_phase" not in meta:
        phase = RING_ACTIVATION_PHASE.get(ring)
        if phase is not None:
            meta["activation_phase"] = phase


def _read_index(repo_root: Path) -> dict[str, dict[str, Any]]:
    index_path = _resolve_within_repo(repo_root, RETRIEVAL_INDEX_FILENAME)
    doc = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise KernelIndexEntryMissingError(f"{RETRIEVAL_INDEX_FILENAME} is not a mapping")
    files = doc.get("files")
    if not isinstance(files, dict):
        raise KernelIndexEntryMissingError(f"{RETRIEVAL_INDEX_FILENAME} missing 'files' mapping")
    return files


def _select_canonical_paths(files: dict[str, dict[str, Any]]) -> list[str]:
    selected: list[str] = []
    for path, meta in files.items():
        if not isinstance(path, str) or not path.startswith(CANONICAL_KERNEL_ROOT):
            continue
        tags = meta.get("tags") if isinstance(meta, dict) else None
        if not isinstance(tags, list) or CANONICAL_KERNEL_TAG not in tags:
            continue
        # Restrict to real kernel artifact suffixes only.
        if not path.endswith((".yaml", ".yml", ".md")):
            continue
        selected.append(path)
    selected.sort()
    return selected


class KernelRegistry:
    """Content-addressed canonical kernel registry.

    Instantiate via :meth:`load`. A registry instance holds an immutable
    snapshot of the kernels discovered at load time; subsequent filesystem
    changes have no effect until a new registry is loaded (see §37, cache
    correctness).
    """

    def __init__(
        self,
        *,
        repo_root: Path,
        kernels_by_id: dict[str, KernelDefinition],
        indexed_paths: dict[str, str],
    ) -> None:
        self._repo_root = repo_root
        self._kernels = kernels_by_id
        self._indexed_paths = indexed_paths

    @property
    def repo_root(self) -> Path:
        return self._repo_root

    @classmethod
    def load(cls, repo_root: str | Path) -> "KernelRegistry":
        root = Path(repo_root)
        if not root.exists():
            raise KernelNotFoundError(f"repo_root does not exist: {root}")
        files = _read_index(root)
        canonical_paths = _select_canonical_paths(files)
        schema = _load_canonical_schema(root)
        validator = Draft202012Validator(schema)

        seen_ids: dict[str, str] = {}
        kernels: dict[str, KernelDefinition] = {}

        for rel in canonical_paths:
            abs_path = _resolve_within_repo(root, rel)
            if not abs_path.exists():
                raise KernelNotFoundError(f"indexed canonical kernel missing on disk: {rel}")
            indexed_sha = files[rel].get("sha256")
            if not isinstance(indexed_sha, str):
                raise KernelIndexEntryMissingError(f"index entry for {rel} has no sha256")
            raw_bytes = abs_path.read_bytes()
            verified_sha = sha256_bytes(raw_bytes)
            if verified_sha != indexed_sha:
                raise KernelDigestMismatchError(
                    f"integrity failure for {rel}: "
                    f"indexed={indexed_sha[:12]} verified={verified_sha[:12]}"
                )
            text = raw_bytes.decode("utf-8")
            if rel.endswith(".md"):
                meta = _parse_markdown_kernel(text, rel)
            else:
                meta = _parse_yaml_kernel(text)
            _apply_mechanical_derivations(meta)

            # Two-phase validation: retain parseable kernels even when
            # schema-invalid; resolvers refuse them at selection time.
            schema_errors = [
                f"{'/'.join(str(p) for p in err.absolute_path) or '(root)'}: {err.message}"
                for err in validator.iter_errors(meta)
            ]
            schema_valid = not schema_errors
            # Additional deterministic checks for enum-like fields, guarding
            # against permissive documents that JSON schema might not enforce
            # (e.g. missing key entirely).
            if meta.get("status") not in VALID_STATUS and schema_valid:
                schema_valid = False
                schema_errors.append(
                    f"status: {meta.get('status')!r} not in {sorted(VALID_STATUS)}"
                )
            if meta.get("activation_phase") not in VALID_ACTIVATION_PHASE and schema_valid:
                schema_valid = False
                schema_errors.append(
                    f"activation_phase: {meta.get('activation_phase')!r} "
                    f"not in {sorted(VALID_ACTIVATION_PHASE)}"
                )

            kernel_id = meta.get("kernel_id")
            if not isinstance(kernel_id, str) or not kernel_id:
                # An indexed 'kernels'-tagged artifact with no recoverable
                # kernel_id is a data defect. Fail closed rather than
                # register a nameless kernel definition.
                raise KernelSchemaInvalidError(f"kernel at {rel} has no kernel_id after parsing")

            if kernel_id in seen_ids:
                raise KernelDuplicateIdError(
                    f"duplicate kernel_id {kernel_id!r} in {seen_ids[kernel_id]} and {rel}"
                )
            seen_ids[kernel_id] = rel

            definition = KernelDefinition(
                kernel_id=kernel_id,
                version=str(meta.get("version") or "0.0.0"),
                ring=str(meta.get("ring") or "R5"),
                category=str(meta.get("category") or "unspecified"),
                title=str(meta.get("title") or kernel_id),
                purpose=str(meta.get("purpose") or ""),
                activation_phase=str(meta.get("activation_phase") or "on_demand"),
                status=str(meta.get("status") or "active"),
                overload_weight=float(meta.get("overload_weight") or 0.0),
                hard_bans=tuple(_as_str_list(meta.get("hard_bans"))),
                fail_closed=bool(meta.get("fail_closed", False)),
                requires=tuple(_as_str_list(meta.get("requires"))),
                routing_hints=_as_str_dict(meta.get("routing_hints")),
                canonical_path=rel,
                sha256=verified_sha,
                schema_valid=schema_valid,
                schema_errors=tuple(schema_errors),
                raw_metadata=_freeze_metadata(meta),
            )
            kernels[kernel_id] = definition

        indexed_paths = {kid: kd.canonical_path for kid, kd in kernels.items()}
        return cls(
            repo_root=root,
            kernels_by_id=kernels,
            indexed_paths=indexed_paths,
        )

    def get(self, kernel_id: str) -> KernelDefinition:
        try:
            return self._kernels[kernel_id]
        except KeyError as exc:
            raise KernelNotFoundError(
                f"unknown kernel_id: {kernel_id}", kernel_id=kernel_id
            ) from exc

    def list_active(self) -> list[KernelDefinition]:
        return sorted(
            (k for k in self._kernels.values() if k.status == "active"),
            key=lambda k: k.kernel_id,
        )

    def all(self) -> list[KernelDefinition]:
        return sorted(self._kernels.values(), key=lambda k: k.kernel_id)

    def has(self, kernel_id: str) -> bool:
        return kernel_id in self._kernels

    def verify_integrity(self) -> None:
        """Re-verify each registered kernel's on-disk SHA against its record.

        Intended for callers that want an explicit re-check (e.g. long-lived
        server processes). Load-time verification is already mandatory.
        """

        for kernel in self._kernels.values():
            abs_path = _resolve_within_repo(self._repo_root, kernel.canonical_path)
            verified = sha256_file(abs_path)
            if verified != kernel.sha256:
                raise KernelDigestMismatchError(
                    f"integrity drift for {kernel.canonical_path}: "
                    f"registered={kernel.sha256[:12]} now={verified[:12]}",
                    kernel_id=kernel.kernel_id,
                )


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return []
    return [str(v) for v in value if v is not None]


def _as_str_dict(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(k): v for k, v in value.items()}


def _freeze_metadata(meta: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy safe to store as raw_metadata."""

    return {str(k): v for k, v in meta.items()}
