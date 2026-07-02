# Architecture — L9 Graph Export Adapter

## Design principle

The context repo remains canonical. The graph is a projection containing pointers, relationships, metadata, and runtime state.

## Components

```text
V2 index
  -> graph_export.exporter
  -> graph-seed JSONL
  -> graph_import.ingester
  -> local report sink or Graphiti sink
  -> graph_sync.syncer
```

## Single ingress

The sync CLI is the single operational ingress for export + verify + ingest. It validates once, produces traceable reports, and fails closed on invalid seed files.

## Contracts

- `artifact-node.schema.json`
- `artifact-edge.schema.json`
- `graph-seed.schema.json`

## Deterministic output

Records are written as sorted-key compact JSONL. This enables diff-friendly CI, reproducible exports, and content-hash comparisons.

## Extension points

- Replace `JsonlReportSink` with a Graphiti-backed sink.
- Add edge extractors for references, governs, validates, implements, and routes_to relationships.
- Add incremental sync using `content_hash` and previous graph state.
