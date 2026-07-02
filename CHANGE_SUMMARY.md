# Change Summary

## Added

- Graph export adapter package under `src/l9_ops_mcp/adapters/graph_export`.
- Graph import adapter with deterministic local report sink.
- Graph sync adapter for export + ingest orchestration.
- CLI scripts for export, ingest, sync, and verification.
- JSON schemas for graph seed records, artifact nodes, and artifact edges.
- Integration docs for adapter operation, consumer contract, Graphiti deployment, and hydrator integration.
- Tests and fixtures covering export, ingest, and sync.

## Consolidated

- Previous graph export adapter pack responsibilities are retained and expanded.
- The suggested `GRAPH_EXPORT_ADAPTER_CONSUMER.md` is now included.
- Runtime repo alignment is corrected for `Quantum-L9/L9-Ops-MCP` as the context/control-plane repository.
