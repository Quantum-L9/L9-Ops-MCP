from pathlib import Path

from l9_ops_mcp.adapters.graph_sync import sync_graph_from_index


def test_sync_graph_from_index_exports_and_ingests(tmp_path: Path) -> None:
    seed = tmp_path / "graph-seed.jsonl"
    report_path = tmp_path / "ingest-report.json"

    report = sync_graph_from_index(Path("tests/fixtures/v2-index.json"), Path("."), seed, report_path)

    assert report["status"] == "pass"
    assert seed.exists()
    assert report_path.exists()
