"""Graph export adapter for L9-Ops-MCP.

Converts V2 metadata/retrieval indexes into graph-seed JSONL records that can be
stored in Graphiti/Neo4j or used as a deterministic graph projection of the
canonical context repository.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable
import hashlib
import json
import re
import time


class GraphExportError(ValueError):
    """Raised when an index or graph-seed record is invalid."""


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
        if not self.id:
            raise GraphExportError("artifact node id is required")
        if not self.artifact_type:
            raise GraphExportError(f"{self.id}: artifact_type is required")
        if not self.source_path:
            raise GraphExportError(f"{self.id}: source_path is required")
        if self.callable and self.mcp_primitive in {"none", "", None}:  # type: ignore[comparison-overlap]
            raise GraphExportError(f"{self.id}: callable artifacts require an mcp_primitive")
        if self.token_cost_estimate is not None and self.token_cost_estimate < 0:
            raise GraphExportError(f"{self.id}: token_cost_estimate must be non-negative")

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
        if not self.relation:
            raise GraphExportError(f"{self.source_id}->{self.target_id}: relation is required")
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


def _load_index(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise GraphExportError(f"index file not found: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GraphExportError(f"invalid JSON index: {path}: {exc}") from exc
    if isinstance(data, dict):
        for key in ("artifacts", "items", "records", "documents", "resources"):
            if isinstance(data.get(key), list):
                return [dict(x) for x in data[key] if isinstance(x, dict)]
        if "path" in data or "source_path" in data:
            return [data]
    if isinstance(data, list):
        return [dict(x) for x in data if isinstance(x, dict)]
    raise GraphExportError("index must be a list or object containing artifacts/items/records")


def node_from_index_item(item: dict[str, Any], repo_root: Path, namespace: str = "core") -> ArtifactNode:
    source_path = str(item.get("source_path") or item.get("path") or item.get("file") or "")
    artifact_id = str(item.get("id") or item.get("artifact_id") or _stable_id_from_path(source_path))
    artifact_type = str(item.get("artifact_type") or item.get("type") or "unknown")
    content_hash = item.get("content_hash") or item.get("sha256") or _file_hash(repo_root, source_path)

    token_cost = item.get("token_cost_estimate") or item.get("token_cost")
    if token_cost is None and source_path:
        candidate = repo_root / source_path
        if candidate.exists() and candidate.is_file():
            token_cost = _estimate_tokens(candidate.read_text(encoding="utf-8", errors="ignore"))

    return ArtifactNode(
        id=artifact_id,
        title=item.get("title") or item.get("name"),
        artifact_type=artifact_type,
        source_path=source_path,
        authority=str(item.get("authority") or "canonical_repo"),
        namespace=str(item.get("namespace") or namespace),
        mcp_primitive=str(item.get("mcp_primitive") or "resource"),
        retrievable=bool(item.get("retrievable", True)),
        injectable=bool(item.get("injectable", False)),
        callable=bool(item.get("callable", False)),
        content_hash=str(content_hash) if content_hash else None,
        token_cost_estimate=int(token_cost) if token_cost is not None else None,
        activation_signals=_as_tuple(item.get("activation_signals") or item.get("retrieval_keys") or item.get("tags")),
        dependencies=_as_tuple(item.get("dependencies") or item.get("depends_on") or item.get("requires")),
        sharing_scope=str(item.get("sharing_scope") or "shared"),
        version=str(item.get("version")) if item.get("version") is not None else None,
    )


def edges_from_node(node: ArtifactNode) -> list[ArtifactEdge]:
    edges: list[ArtifactEdge] = []
    for dep in node.dependencies:
        edges.append(ArtifactEdge(node.id, dep, "depends_on", "dependencies"))
    for signal in node.activation_signals:
        signal_id = "activation_signal." + re.sub(r"[^A-Za-z0-9_.-]+", "_", signal.lower()).strip("_")
        if signal_id != node.id:
            edges.append(ArtifactEdge(node.id, signal_id, "activates_on", "activation_signals", confidence=0.85))
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


def verify_graph_seed(path: Path) -> dict[str, Any]:
    records = read_jsonl(path)
    node_ids: set[str] = set()
    edges: list[dict[str, Any]] = []
    failures: list[str] = []

    for idx, record in enumerate(records, start=1):
        if record.get("record_type") == "artifact_node":
            artifact = record.get("artifact") or {}
            try:
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
                node_ids.add(node.id)
            except Exception as exc:  # noqa: BLE001 - validation must collect evidence
                failures.append(f"record {idx}: {exc}")
        elif record.get("record_type") == "artifact_edge":
            edge = record.get("edge") or {}
            try:
                candidate = ArtifactEdge(
                    source_id=str(edge.get("source_id", "")),
                    target_id=str(edge.get("target_id", "")),
                    relation=str(edge.get("relation", "")),
                    evidence=str(edge.get("evidence", "")),
                    confidence=float(edge.get("confidence", 1.0)),
                    provenance=str(edge.get("provenance", "metadata_index")),
                )
                candidate.validate()
                edges.append(edge)
            except Exception as exc:  # noqa: BLE001
                failures.append(f"record {idx}: {exc}")
        else:
            failures.append(f"record {idx}: unsupported record_type {record.get('record_type')!r}")

    dangling_edges = [
        f"{edge.get('source_id')}->{edge.get('target_id')}"
        for edge in edges
        if edge.get("source_id") not in node_ids and not str(edge.get("source_id", "")).startswith("activation_signal.")
    ]

    status = "pass" if not failures else "fail"
    return {
        "status": status,
        "record_count": len(records),
        "node_count": len(node_ids),
        "edge_count": len(edges),
        "failures": failures,
        "warnings": {"dangling_edges": dangling_edges},
    }
