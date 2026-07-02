# L9 Graph Export Adapter Overlay

Enterprise-grade PR-ready overlay for `Quantum-L9/L9-Ops-MCP`.

## Purpose

This pack closes the graph export gap between the L9 metadata injection pipeline and the shared Graphiti/MCP memory runtime.

It converts V2 metadata or retrieval indexes into deterministic `graph-seed.jsonl` records, validates the seed contract, optionally ingests the seed into a sink, and provides an end-to-end sync command.

## Architecture

```text
L9 context repo
  -> V2 metadata injector / retrieval index
  -> graph export adapter
  -> graph-seed.jsonl
  -> graph import / Graphiti sink
  -> shared agent memory graph
  -> hydrator RuntimePayload
```

## Quick start

```bash
python -m pytest
python scripts/export_graph_seed.py --index tests/fixtures/v2-index.json --repo-root . --out /tmp/graph-seed.jsonl
python scripts/verify_graph.py --seed /tmp/graph-seed.jsonl
python scripts/ingest_graph_seed.py --seed /tmp/graph-seed.jsonl --report /tmp/graph-ingest-report.json
python scripts/sync_graph.py --index tests/fixtures/v2-index.json --repo-root . --seed /tmp/graph-seed.jsonl --report /tmp/graph-ingest-report.json
```

## Files

See `MANIFEST.md` for the complete file inventory and validation status.

## Scope

Included:
- V2 index to graph seed export.
- Artifact node and edge schemas.
- Deterministic local ingestion report sink.
- End-to-end sync pipeline.
- Docs for adapter, consumer, Graphiti deployment, and hydrator integration.
- Tests and fixtures.

Not included:
- Credentials.
- Live Graphiti server configuration.
- Repository-specific secret values.
- Automatic writeback to production graph without operator wiring.
