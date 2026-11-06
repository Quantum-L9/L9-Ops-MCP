# >>> l9:meta >>>
# id: L9-Ops-MCP.test.tests_test_ingest__py
# title: test ingest
# artifact_type: test
# mcp_primitive: none
# callable: false
# retrievable: false
# injectable: false
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: tests/test_ingest.py
# content_hash: 70876f615eb425e206a23bf566909eb8ecbbeacf78825666cf77e6cf144bd6eb
# token_cost_estimate: 149
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
from pathlib import Path

from l9_ops_mcp.adapters.graph_export import export_graph_seed
from l9_ops_mcp.adapters.graph_import import JsonlReportSink, ingest_graph_seed


def test_ingest_graph_seed_writes_report(tmp_path: Path) -> None:
    seed = tmp_path / "graph-seed.jsonl"
    report_path = tmp_path / "ingest-report.json"
    export_graph_seed(Path("tests/fixtures/v2-index.json"), Path("."), seed)

    report = ingest_graph_seed(seed, JsonlReportSink(report_path))

    assert report["status"] == "pass"
    assert report_path.exists()
    assert report["ingestion"]["node_count"] == 2
