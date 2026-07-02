# RUNBOOK — Graph Export Adapter Overlay

## Prerequisites

- Python 3.11+
- Existing `Quantum-L9/L9-Ops-MCP` checkout
- A generated V2 metadata or retrieval index

## Install in repo

Copy this overlay into the root of `L9-Ops-MCP`.

Expected resulting paths:

```text
docs/integrations/
schemas/
scripts/
src/l9_ops_mcp/adapters/
tests/
```

## Validate

```bash
python -m pytest
python -m compileall src scripts tests
```

Optional if `ruff` is installed:

```bash
ruff check .
```

## Export graph seed

```bash
python scripts/export_graph_seed.py \
  --index path/to/retrieval-index.json \
  --repo-root . \
  --out runtime/graph/graph-seed.jsonl \
  --namespace core
```

## Verify graph seed

```bash
python scripts/verify_graph.py --seed runtime/graph/graph-seed.jsonl
```

## Ingest to local report sink

```bash
python scripts/ingest_graph_seed.py \
  --seed runtime/graph/graph-seed.jsonl \
  --report runtime/graph/graph-ingest-report.json
```

## Full sync

```bash
python scripts/sync_graph.py \
  --index path/to/retrieval-index.json \
  --repo-root . \
  --seed runtime/graph/graph-seed.jsonl \
  --report runtime/graph/graph-ingest-report.json
```

## Troubleshooting

- `index file not found`: verify the V2 index path.
- `invalid JSON index`: regenerate the V2 index or repair malformed JSON.
- `callable artifacts require an mcp_primitive`: fix metadata so callable artifacts declare the tool/resource primitive.
- `unsupported record_type`: ensure JSONL lines match `artifact_node` or `artifact_edge`.

## Rollback

Remove the overlay files listed in `MANIFEST.md`, or revert the PR.
