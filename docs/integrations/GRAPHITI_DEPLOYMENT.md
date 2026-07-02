# Graphiti Deployment

## Recommended deployment

```text
L9-Ops-MCP repo
  -> V2 metadata index
  -> graph-seed.jsonl
  -> Graphiti sink
  -> Neo4j
```

## Environment

Required values are deployment-specific and must not be committed:

- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- Graphiti service configuration

## Safe rollout

1. Export graph seed locally.
2. Verify JSONL.
3. Ingest into local report sink.
4. Ingest into staging Graphiti.
5. Run hydrator read checks.
6. Promote to production sync.

## Production sink implementation

Implement `GraphSeedSink.ingest(records)` using the installed Graphiti client. Preserve the seed contract and return a structured report with status, node count, edge count, failures, and warnings.
