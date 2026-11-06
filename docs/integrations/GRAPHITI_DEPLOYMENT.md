---
id: "L9-Ops-MCP.context.docs_integrations_graphiti_deployment__md"
title: "GRAPHITI DEPLOYMENT"
artifact_type: "context"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/integrations/GRAPHITI_DEPLOYMENT.md"
content_hash: "572a7bc673c47ac9826cd9f5a94e7eec5e23bced2a3dd5fff5714548400539aa"
token_cost_estimate: 187
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "legal"
description: "Unknown"
activation_signals: ["contract"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
---
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
