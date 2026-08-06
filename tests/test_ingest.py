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
