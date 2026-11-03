# >>> l9:meta >>>
# id: L9-Ops-MCP.test.tests_test_export__py
# title: test export
# artifact_type: test
# mcp_primitive: none
# callable: false
# retrievable: false
# injectable: false
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: tests/test_export.py
# content_hash: 4faaf82ad3d5f1de479fbb3ffe7ab0afe141c81ded6e65a238f0a75f20b1fa7e
# token_cost_estimate: 242
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
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
