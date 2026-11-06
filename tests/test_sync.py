# >>> l9:meta >>>
# id: L9-Ops-MCP.test.tests_test_sync__py
# title: test sync
# artifact_type: test
# mcp_primitive: none
# callable: false
# retrievable: false
# injectable: false
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: tests/test_sync.py
# content_hash: c55266df60653f14f35aef31c6e302cb197eeabb2b20cf9b5258707785c67d84
# token_cost_estimate: 119
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
from pathlib import Path

from l9_ops_mcp.adapters.graph_sync import sync_graph_from_index


def test_sync_graph_from_index_exports_and_ingests(tmp_path: Path) -> None:
    seed = tmp_path / "graph-seed.jsonl"
    report_path = tmp_path / "ingest-report.json"

    report = sync_graph_from_index(
        Path("tests/fixtures/v2-index.json"), Path("."), seed, report_path
    )

    assert report["status"] == "pass"
    assert seed.exists()
    assert report_path.exists()
