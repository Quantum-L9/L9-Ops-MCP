from pathlib import Path
import json
import subprocess
import sys
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from l9_ops_mcp.adapters.graph_export import export_graph_seed, exporter, verify_graph_seed


def test_export_graph_seed_creates_nodes_and_edges(tmp_path: Path) -> None:
    index = Path("tests/fixtures/v2-index.json")
    out = tmp_path / "graph-seed.jsonl"

    report = export_graph_seed(index, Path("."), out, namespace="core")

    assert report["status"] == "pass"
    assert report["node_count"] == 2
    assert out.exists()
    records = [json.loads(line) for line in out.read_text().splitlines()]
    assert any(r["record_type"] == "artifact_node" for r in records)
    assert any(r["record_type"] == "artifact_edge" for r in records)


def test_verify_graph_seed_passes_export(tmp_path: Path) -> None:
    out = tmp_path / "graph-seed.jsonl"
    export_graph_seed(Path("tests/fixtures/v2-index.json"), Path("."), out)
    report = verify_graph_seed(out)
    assert report["status"] == "pass"
    assert report["node_count"] == 2


# --- WU-33 regression: repository index, schema validity, strict verification ---

REPO = Path(__file__).resolve().parents[1]
SCHEMAS = REPO / "schemas"
REPO_INDEX = REPO / "AGENT_RETRIEVAL_INDEX.yaml"


def _seed_validator() -> Draft202012Validator:
    registry: Registry[Any] = Registry()
    for name in ("artifact-node.schema.json", "artifact-edge.schema.json"):
        contents = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
        registry = registry.with_resource(name, Resource.from_contents(contents))
    schema = json.loads((SCHEMAS / "graph-seed.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=registry)


def _schema_errors(records: list[dict[str, Any]]) -> list[str]:
    validator = _seed_validator()
    return [
        f"record {i}: {err.message}"
        for i, record in enumerate(records, start=1)
        for err in validator.iter_errors(record)
    ]


def _records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_export_accepts_retrieval_index_files_map(tmp_path: Path) -> None:
    out = tmp_path / "graph-seed.jsonl"
    report = export_graph_seed(REPO_INDEX, REPO, out)
    files = yaml.safe_load(REPO_INDEX.read_text(encoding="utf-8"))["files"]
    assert report["status"] == "pass"
    assert report["node_count"] == len(files)
    nodes = {r["artifact"]["source_path"]: r["artifact"] for r in _records(out) if "artifact" in r}
    assert set(nodes) == set(files)
    sample_path, sample = next(iter(files.items()))
    assert nodes[sample_path]["content_hash"] == sample["sha256"]
    assert nodes[sample_path]["artifact_type"] == sample["role"]
    assert verify_graph_seed(out)["status"] == "pass"


@pytest.mark.parametrize("index", [REPO_INDEX, REPO / "tests/fixtures/v2-index.json"])
def test_exported_records_validate_against_graph_seed_schema(tmp_path: Path, index: Path) -> None:
    out = tmp_path / "graph-seed.jsonl"
    export_graph_seed(index, REPO, out)
    records = _records(out)
    assert records
    assert _schema_errors(records) == []


def test_schema_rejects_mixed_and_unknown_records() -> None:
    node = {"id": "a", "artifact_type": "t", "source_path": "a.md", "authority": "canonical_repo",
            "namespace": "core", "mcp_primitive": "resource", "retrievable": True,
            "injectable": False, "callable": False, "sharing_scope": "shared"}  # fmt: skip
    assert _schema_errors([{"record_type": "artifact_node", "artifact": node}]) == []
    assert _schema_errors([{"record_type": "artifact_node", "artifact": node, "x": 1}])
    assert _schema_errors([{"record_type": "artifact_edge", "artifact": node}])
    assert _schema_errors([{"record_type": "other", "artifact": node}])


def test_exporter_enums_match_schemas() -> None:
    node_schema = json.loads((SCHEMAS / "artifact-node.schema.json").read_text(encoding="utf-8"))
    edge_schema = json.loads((SCHEMAS / "artifact-edge.schema.json").read_text(encoding="utf-8"))
    props = node_schema["properties"]
    assert set(props["authority"]["enum"]) == exporter.AUTHORITIES
    assert set(props["sharing_scope"]["enum"]) == exporter.SHARING_SCOPES
    assert set(edge_schema["properties"]["relation"]["enum"]) == exporter.RELATIONS


def _node(node_id: str, **overrides: Any) -> dict[str, Any]:
    artifact = {
        "id": node_id,
        "artifact_type": "context",
        "source_path": f"{node_id}.md",
        "authority": "canonical_repo",
        "namespace": "core",
        "mcp_primitive": "resource",
        "retrievable": True,
        "injectable": False,
        "callable": False,
        "sharing_scope": "shared",
    }
    artifact.update(overrides)
    return {"record_type": "artifact_node", "artifact": artifact}


def _edge(source: str, target: str, relation: str = "depends_on") -> dict[str, Any]:
    return {
        "record_type": "artifact_edge",
        "edge": {
            "source_id": source,
            "target_id": target,
            "relation": relation,
            "evidence": "dependencies",
            "confidence": 1.0,
            "provenance": "metadata_index",
        },
    }


INVALID_SEEDS = {
    "dangling_target": [_node("a"), _edge("a", "missing")],
    "duplicate_node_id": [_node("a"), _node("a")],
    "invalid_enum": [_node("a", authority="bogus"), _node("b"), _edge("a", "b", relation="bogus")],
    "empty": [],
}


@pytest.mark.parametrize("name", sorted(INVALID_SEEDS))
def test_verify_rejects_invalid_seeds(tmp_path: Path, name: str) -> None:
    seed = tmp_path / f"{name}.jsonl"
    seed.write_text("".join(json.dumps(r) + "\n" for r in INVALID_SEEDS[name]), encoding="utf-8")
    report = verify_graph_seed(seed)
    assert report["status"] == "fail", report
    assert report["failures"]


def test_verify_accepts_closed_graph(tmp_path: Path) -> None:
    seed = tmp_path / "ok.jsonl"
    records = [
        _node("a"),
        _node("b"),
        _edge("a", "b"),
        _edge("a", "activation_signal.x", "activates_on"),
    ]
    seed.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    assert verify_graph_seed(seed)["status"] == "pass"


def test_verify_cli_validates_schema(tmp_path: Path) -> None:
    seed = tmp_path / "extra.jsonl"
    record = _node("a")
    record["artifact"]["unexpected"] = 1
    seed.write_text(json.dumps(record) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "scripts/verify_graph.py", "--seed", str(seed),
         "--schema", "schemas/graph-seed.schema.json"],
        cwd=REPO, capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "unexpected" in proc.stdout


def test_make_graph_targets_run_from_repository_data(tmp_path: Path) -> None:
    out = tmp_path / "graph"
    for target in ("graph-export", "graph-verify", "graph-sync"):
        proc = subprocess.run(
            ["make", "-s", target, f"PYTHON={sys.executable}", f"GRAPH_OUT={out}"],
            cwd=REPO, capture_output=True, text=True, timeout=300, check=False,
        )  # fmt: skip
        assert proc.returncode == 0, f"make {target}: {proc.stdout}{proc.stderr}"
    assert _schema_errors(_records(out / "graph-seed.jsonl")) == []
    assert json.loads((out / "ingest-report.json").read_text())["status"] == "pass"
