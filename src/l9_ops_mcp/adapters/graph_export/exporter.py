"""Graph export adapter for L9-Ops-MCP.

Converts V2 metadata/retrieval indexes into graph-seed JSONL records that can be
stored in Graphiti/Neo4j or used as a deterministic graph projection of the
canonical context repository.

Accepted index inputs: the repository's ``AGENT_RETRIEVAL_INDEX.yaml`` (a
``files`` map of ``path -> {role, sha256, tags, retrieval}``), or a JSON/YAML
list / ``artifacts``-style object of artifact items.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import hashlib
import json
import re
import time

import yaml


class GraphExportError(ValueError):
    """Raised when an index or graph-seed record is invalid."""


# Closed vocabularies; kept in lockstep with schemas/artifact-node.schema.json
# and schemas/artifact-edge.schema.json (tests/test_export.py enforces it).
AUTHORITIES = frozenset({"canonical_repo", "metadata_index", "unknown"})
SHARING_SCOPES = frozenset({"shared", "private", "restricted", "unknown"})
RELATIONS = frozenset(
    {"depends_on", "activates_on", "implements", "governs", "validates", "routes_to", "references"}
)
ACTIVATION_SIGNAL_PREFIX = "activation_signal."


@dataclass(frozen=True)
class ArtifactNode:
    """Canonical graph projection for one context-repo artifact."""

    id: str
    artifact_type: str
    source_path: str
    authority: str = "canonical_repo"
    title: str | None = None
    namespace: str = "core"
    mcp_primitive: str = "resource"
    retrievable: bool = True
    injectable: bool = False
    callable: bool = False
    content_hash: str | None = None
    token_cost_estimate: int | None = None
    activation_signals: tuple[str, ...] = field(default_factory=tuple)
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    sharing_scope: str = "shared"
    version: str | None = None

    def validate(self) -> None:
        self._validate_required_fields()
        self._validate_vocabularies()
        if self.callable and self.mcp_primitive in {"none", ""}:
            raise GraphExportError(f"{self.id}: callable artifacts require an mcp_primitive")
        if self.token_cost_estimate is not None and self.token_cost_estimate < 0:
            raise GraphExportError(f"{self.id}: token_cost_estimate must be non-negative")

    def _validate_required_fields(self) -> None:
        if not self.id:
            raise GraphExportError("artifact node id is required")
        for name in ("artifact_type", "source_path", "namespace"):
            if not getattr(self, name):
                raise GraphExportError(f"{self.id}: {name} is required")

    def _validate_vocabularies(self) -> None:
        if self.authority not in AUTHORITIES:
            raise GraphExportError(f"{self.id}: authority {self.authority!r} is not allowed")
        if self.sharing_scope not in SHARING_SCOPES:
            raise GraphExportError(
                f"{self.id}: sharing_scope {self.sharing_scope!r} is not allowed"
            )

    def to_record(self) -> dict[str, Any]:
        self.validate()
        return {"record_type": "artifact_node", "artifact": _drop_none(asdict(self))}


@dataclass(frozen=True)
class ArtifactEdge:
    """Typed relationship between two artifact nodes."""

    source_id: str
    target_id: str
    relation: str
    evidence: str
    confidence: float = 1.0
    provenance: str = "metadata_index"

    def validate(self) -> None:
        if not self.source_id or not self.target_id:
            raise GraphExportError("edge source_id and target_id are required")
        if self.source_id == self.target_id:
            raise GraphExportError(f"{self.source_id}: self edges are not allowed")
        if self.relation not in RELATIONS:
            raise GraphExportError(
                f"{self.source_id}->{self.target_id}: relation {self.relation!r} is not allowed"
            )
        if not self.evidence or not self.provenance:
            raise GraphExportError(
                f"{self.source_id}->{self.target_id}: evidence and provenance are required"
            )
        if not (0 <= self.confidence <= 1):
            raise GraphExportError(f"{self.source_id}->{self.target_id}: confidence must be 0..1")

    def to_record(self) -> dict[str, Any]:
        self.validate()
        return {"record_type": "artifact_edge", "edge": _drop_none(asdict(self))}


def _drop_none(data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if v is not None}


def _stable_id_from_path(path: str) -> str:
    stem = path.strip("/").replace("\\", "/")
    stem = re.sub(r"\.(md|yaml|yml|json|py|txt)$", "", stem, flags=re.I)
    stem = re.sub(r"[^A-Za-z0-9_.\-\/]+", "-", stem)
    return stem.replace("/", ".")


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value else ()
    if isinstance(value, list | tuple | set):
        return tuple(str(v) for v in value if str(v))
    return (str(value),)


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / 4))


def _file_hash(repo_root: Path, source_path: str) -> str | None:
    candidate = (repo_root / source_path).resolve()
    try:
        root = repo_root.resolve()
        candidate.relative_to(root)
    except ValueError:
        return None
    if not candidate.exists() or not candidate.is_file():
        return None
    return hashlib.sha256(candidate.read_bytes()).hexdigest()


def _items_from_files_map(files: dict[str, Any]) -> list[dict[str, Any]]:
    """Map AGENT_RETRIEVAL_INDEX.yaml ``files`` entries to exporter index items."""
    items: list[dict[str, Any]] = []
    for source_path, entry in files.items():
        meta = entry if isinstance(entry, dict) else {}
        item: dict[str, Any] = {"source_path": str(source_path)}
        if meta.get("role"):
            item["artifact_type"] = meta["role"]
        if meta.get("sha256"):
            item["content_hash"] = meta["sha256"]
        if meta.get("tags"):
            item["tags"] = meta["tags"]
        items.append(item)
    return items


def _parse_index_text(path: Path, text: str) -> Any:
    """Parse index text as YAML or JSON according to the file suffix."""
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            return yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise GraphExportError(f"invalid YAML index: {path}: {exc}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise GraphExportError(f"invalid JSON index: {path}: {exc}") from exc


def _items_from_index_object(data: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Return the items of an object-shaped index, or None when it holds none."""
    if isinstance(data.get("files"), dict):
        return _items_from_files_map(data["files"])
    for key in ("artifacts", "items", "records", "documents", "resources"):
        if isinstance(data.get(key), list):
            return [dict(x) for x in data[key] if isinstance(x, dict)]
    if "path" in data or "source_path" in data:
        return [data]
    return None


def _load_index(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise GraphExportError(f"index file not found: {path}")
    data = _parse_index_text(path, path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        items = _items_from_index_object(data)
        if items is not None:
            return items
    if isinstance(data, list):
        return [dict(x) for x in data if isinstance(x, dict)]
    raise GraphExportError(
        "index must be a list or object containing files/artifacts/items/records"
    )


def _first_truthy(item: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Equivalent of ``item.get(k1) or item.get(k2) or ...`` over ``keys``."""
    value: Any = None
    for key in keys:
        value = item.get(key)
        if value:
            return value
    return value


def _str_or_default(item: dict[str, Any], key: str, default: str) -> str:
    return str(item.get(key) or default)


def _token_cost(item: dict[str, Any], repo_root: Path, source_path: str) -> Any:
    """Declared token cost, else an estimate from the source file when it exists."""
    token_cost = _first_truthy(item, ("token_cost_estimate", "token_cost"))
    if token_cost is None and source_path:
        candidate = repo_root / source_path
        if candidate.exists() and candidate.is_file():
            token_cost = _estimate_tokens(candidate.read_text(encoding="utf-8", errors="ignore"))
    return token_cost


def node_from_index_item(
    item: dict[str, Any], repo_root: Path, namespace: str = "core"
) -> ArtifactNode:
    source_path = str(_first_truthy(item, ("source_path", "path", "file")) or "")
    artifact_id = str(
        _first_truthy(item, ("id", "artifact_id")) or _stable_id_from_path(source_path)
    )
    artifact_type = str(_first_truthy(item, ("artifact_type", "type")) or "unknown")
    content_hash = _first_truthy(item, ("content_hash", "sha256")) or _file_hash(
        repo_root, source_path
    )
    token_cost = _token_cost(item, repo_root, source_path)
    version = item.get("version")

    return ArtifactNode(
        id=artifact_id,
        title=_first_truthy(item, ("title", "name")),
        artifact_type=artifact_type,
        source_path=source_path,
        authority=_str_or_default(item, "authority", "canonical_repo"),
        namespace=_str_or_default(item, "namespace", namespace),
        mcp_primitive=_str_or_default(item, "mcp_primitive", "resource"),
        retrievable=bool(item.get("retrievable", True)),
        injectable=bool(item.get("injectable", False)),
        callable=bool(item.get("callable", False)),
        content_hash=str(content_hash) if content_hash else None,
        token_cost_estimate=int(token_cost) if token_cost is not None else None,
        activation_signals=_as_tuple(
            _first_truthy(item, ("activation_signals", "retrieval_keys", "tags"))
        ),
        dependencies=_as_tuple(_first_truthy(item, ("dependencies", "depends_on", "requires"))),
        sharing_scope=_str_or_default(item, "sharing_scope", "shared"),
        version=str(version) if version is not None else None,
    )


def edges_from_node(node: ArtifactNode) -> list[ArtifactEdge]:
    edges: list[ArtifactEdge] = []
    for dep in node.dependencies:
        edges.append(ArtifactEdge(node.id, dep, "depends_on", "dependencies"))
    for signal in node.activation_signals:
        signal_id = ACTIVATION_SIGNAL_PREFIX + re.sub(
            r"[^A-Za-z0-9_.-]+", "_", signal.lower()
        ).strip("_")
        if signal_id != node.id:
            edges.append(
                ArtifactEdge(
                    node.id, signal_id, "activates_on", "activation_signals", confidence=0.85
                )
            )
    return edges


def export_graph_seed(
    index_path: Path,
    repo_root: Path,
    output_path: Path,
    namespace: str = "core",
    include_edges: bool = True,
) -> dict[str, Any]:
    """Export a V2 metadata/retrieval index to JSONL graph seed records."""

    items = _load_index(index_path)
    records: list[dict[str, Any]] = []
    nodes: list[ArtifactNode] = []

    for item in items:
        node = node_from_index_item(item, repo_root, namespace)
        node.validate()
        nodes.append(node)
        records.append(node.to_record())
        if include_edges:
            for edge in edges_from_node(node):
                edge.validate()
                records.append(edge.to_record())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")

    return {
        "status": "pass",
        "index_path": str(index_path),
        "repo_root": str(repo_root),
        "output_path": str(output_path),
        "node_count": len(nodes),
        "record_count": len(records),
        "generated_at_epoch": int(time.time()),
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise GraphExportError(f"jsonl file not found: {path}")
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise GraphExportError(f"{path}:{line_number}: invalid JSONL: {exc}") from exc
    return records


def _seed_schema_validator(schema_path: Path) -> Any:
    """Build a Draft 2020-12 validator resolving sibling ``$ref`` schema files."""
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    registry: Registry[Any] = Registry()
    for sibling in sorted(schema_path.parent.glob("*.json")):
        try:
            contents = json.loads(sibling.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(contents, dict) and "$schema" in contents:
            registry = registry.with_resource(sibling.name, Resource.from_contents(contents))
    return Draft202012Validator(schema, registry=registry)


def _node_from_seed_artifact(artifact: Any) -> ArtifactNode:
    """Rebuild and validate an ArtifactNode from a seed ``artifact`` payload."""
    node = ArtifactNode(
        id=str(artifact.get("id", "")),
        title=artifact.get("title"),
        artifact_type=str(artifact.get("artifact_type", "")),
        source_path=str(artifact.get("source_path", "")),
        authority=str(artifact.get("authority", "canonical_repo")),
        namespace=str(artifact.get("namespace", "core")),
        mcp_primitive=str(artifact.get("mcp_primitive", "resource")),
        retrievable=bool(artifact.get("retrievable", True)),
        injectable=bool(artifact.get("injectable", False)),
        callable=bool(artifact.get("callable", False)),
        content_hash=artifact.get("content_hash"),
        token_cost_estimate=artifact.get("token_cost_estimate"),
        activation_signals=tuple(artifact.get("activation_signals", [])),
        dependencies=tuple(artifact.get("dependencies", [])),
        sharing_scope=str(artifact.get("sharing_scope", "shared")),
        version=artifact.get("version"),
    )
    node.validate()
    return node


def _edge_from_seed_edge(edge: Any) -> ArtifactEdge:
    """Rebuild and validate an ArtifactEdge from a seed ``edge`` payload."""
    candidate = ArtifactEdge(
        source_id=str(edge.get("source_id", "")),
        target_id=str(edge.get("target_id", "")),
        relation=str(edge.get("relation", "")),
        evidence=str(edge.get("evidence", "")),
        confidence=float(edge.get("confidence", 1.0)),
        provenance=str(edge.get("provenance", "metadata_index")),
    )
    candidate.validate()
    return candidate


@dataclass
class _SeedScan:
    """Evidence accumulated while scanning graph-seed records in order."""

    validator: Any = None
    node_ids: set[str] = field(default_factory=set)
    edges: list[dict[str, Any]] = field(default_factory=list)
    edge_keys: set[tuple[str, str, str]] = field(default_factory=set)
    failures: list[str] = field(default_factory=list)

    def scan(self, idx: int, record: Any) -> None:
        if self.validator is not None:
            for error in self.validator.iter_errors(record):
                self.failures.append(f"record {idx}: schema: {error.message}")
        if not isinstance(record, dict):
            self.failures.append(f"record {idx}: record is not an object")
            return
        if record.get("record_type") == "artifact_node":
            self._scan_node(idx, record)
        elif record.get("record_type") == "artifact_edge":
            self._scan_edge(idx, record)
        else:
            self.failures.append(
                f"record {idx}: unsupported record_type {record.get('record_type')!r}"
            )

    def _scan_node(self, idx: int, record: dict[str, Any]) -> None:
        artifact = record.get("artifact") or {}
        try:
            node = _node_from_seed_artifact(artifact)
        except Exception as exc:  # noqa: BLE001 - validation must collect evidence
            self.failures.append(f"record {idx}: {exc}")
            return
        if node.id in self.node_ids:
            self.failures.append(f"record {idx}: duplicate node id {node.id!r}")
        self.node_ids.add(node.id)

    def _scan_edge(self, idx: int, record: dict[str, Any]) -> None:
        edge = record.get("edge") or {}
        try:
            candidate = _edge_from_seed_edge(edge)
        except Exception as exc:  # noqa: BLE001
            self.failures.append(f"record {idx}: {exc}")
            return
        key = (candidate.source_id, candidate.target_id, candidate.relation)
        if key in self.edge_keys:
            self.failures.append(f"record {idx}: duplicate edge {key[0]}-[{key[2]}]->{key[1]}")
        self.edge_keys.add(key)
        self.edges.append(edge)


def _dangling_edges(edges: list[dict[str, Any]], node_ids: set[str]) -> list[str]:
    """Edges whose source, or non-activation-signal target, is not an exported node."""
    dangling_edges: list[str] = []
    for edge in edges:
        source = str(edge.get("source_id", ""))
        target = str(edge.get("target_id", ""))
        target_ok = target in node_ids or (
            edge.get("relation") == "activates_on" and target.startswith(ACTIVATION_SIGNAL_PREFIX)
        )
        if source not in node_ids or not target_ok:
            dangling_edges.append(f"{source}->{target}")
    return dangling_edges


def verify_graph_seed(path: Path, schema_path: Path | None = None) -> dict[str, Any]:
    """Verify a graph seed; fails on invalid, duplicate, dangling or empty content.

    When ``schema_path`` is given, every record is also validated against that
    JSON Schema (``schemas/graph-seed.schema.json`` in this repository).
    """
    records = read_jsonl(path)
    validator = _seed_schema_validator(schema_path) if schema_path is not None else None

    scan = _SeedScan(validator=validator)
    for idx, record in enumerate(records, start=1):
        scan.scan(idx, record)
    node_ids = scan.node_ids
    edges = scan.edges
    failures = scan.failures

    if not records:
        failures.append("seed is empty: no records")
    elif not node_ids:
        failures.append("seed has no artifact nodes")

    dangling_edges = _dangling_edges(edges, node_ids)
    for dangling in dangling_edges:
        failures.append(f"dangling edge {dangling}: endpoint is not an exported node")

    status = "pass" if not failures else "fail"
    return {
        "status": status,
        "record_count": len(records),
        "node_count": len(node_ids),
        "edge_count": len(edges),
        "failures": failures,
        "warnings": {"dangling_edges": dangling_edges},
    }
