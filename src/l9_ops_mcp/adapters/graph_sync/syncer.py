# >>> l9:meta >>>
# id: L9-Ops-MCP.source.src_l9_ops_mcp_adapters_graph_sync_syncer__py
# title: syncer
# artifact_type: source
# mcp_primitive: resource
# callable: false
# retrievable: true
# injectable: true
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: src/l9_ops_mcp/adapters/graph_sync/syncer.py
# content_hash: 546edb0ae64628b3335a74cd00d468e4df060b29fbeecd9ed29f47a5f2f99658
# token_cost_estimate: 212
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
"""End-to-end graph synchronization pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from l9_ops_mcp.adapters.graph_export.exporter import export_graph_seed
from l9_ops_mcp.adapters.graph_import.ingester import JsonlReportSink, ingest_graph_seed


def sync_graph_from_index(
    index_path: Path,
    repo_root: Path,
    seed_path: Path,
    report_path: Path,
    namespace: str = "core",
) -> dict[str, Any]:
    export_report = export_graph_seed(index_path, repo_root, seed_path, namespace=namespace)
    ingest_report = ingest_graph_seed(seed_path, JsonlReportSink(report_path))
    return {
        "status": "pass"
        if export_report["status"] == "pass" and ingest_report["status"] == "pass"
        else "fail",
        "export": export_report,
        "ingest": ingest_report,
    }
