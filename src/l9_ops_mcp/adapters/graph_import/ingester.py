# >>> l9:meta >>>
# id: L9-Ops-MCP.source.src_l9_ops_mcp_adapters_graph_import_ingester__py
# title: ingester
# artifact_type: source
# mcp_primitive: resource
# callable: false
# retrievable: true
# injectable: true
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: src/l9_ops_mcp/adapters/graph_import/ingester.py
# content_hash: c65b435008d13c28a251249c59c5e8c5862c1b996177cdb78339525633cc1677
# token_cost_estimate: 477
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
"""Graph seed ingestion helpers.

The default sink writes a deterministic ingestion report. Production deployments
can replace GraphitiSink with a client backed by graphiti-core/Neo4j while keeping
the input contract stable.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
import json

from l9_ops_mcp.adapters.graph_export.exporter import read_jsonl, verify_graph_seed


class GraphSeedSink(Protocol):
    def ingest(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """Ingest graph seed records and return a report."""


@dataclass
class JsonlReportSink:
    """Local deterministic sink for CI, dry-runs, and offline deployments."""

    report_path: Path

    def ingest(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        node_count = sum(1 for r in records if r.get("record_type") == "artifact_node")
        edge_count = sum(1 for r in records if r.get("record_type") == "artifact_edge")
        report = {
            "status": "pass",
            "sink": "jsonl_report",
            "record_count": len(records),
            "node_count": node_count,
            "edge_count": edge_count,
        }
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return report


def ingest_graph_seed(seed_path: Path, sink: GraphSeedSink) -> dict[str, Any]:
    verification = verify_graph_seed(seed_path)
    if verification["status"] != "pass":
        return {"status": "fail", "verification": verification, "ingestion": None}
    records = read_jsonl(seed_path)
    ingestion = sink.ingest(records)
    return {
        "status": ingestion.get("status", "unknown"),
        "verification": verification,
        "ingestion": ingestion,
    }
