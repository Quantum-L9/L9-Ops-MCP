from pathlib import Path
import json

from l9_ops_mcp.adapters.graph_export import export_graph_seed, verify_graph_seed


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
