# Decision Log

## D1 — Keep repo canonical, graph projected

Decision: Graph seed contains metadata, relationships, and source pointers, not full canonical doctrine text.

Rationale: Prevent duplicate authority and drift between the context repo and shared memory graph.

## D2 — JSONL as interchange format

Decision: Use sorted-key JSONL for graph seed.

Rationale: Deterministic, diffable, streamable, and simple to ingest into Graphiti, Neo4j, or another graph backend.

## D3 — Local report sink first

Decision: Include a deterministic local ingestion sink instead of hardcoding Graphiti credentials/API behavior.

Rationale: Enables CI validation without secrets and provides a stable adapter boundary for production Graphiti ingestion.

## D4 — Single sync ingress

Decision: Provide `scripts/sync_graph.py` as the single operational path for export + verify + ingest.

Rationale: Reduces operator steps and prevents bypassing validation.
