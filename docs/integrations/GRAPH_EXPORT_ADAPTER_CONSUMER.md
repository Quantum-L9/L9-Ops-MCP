---
id: "L9-Ops-MCP.context.docs_integrations_graph_export_adapter_consumer__md"
title: "GRAPH EXPORT ADAPTER CONSUMER"
artifact_type: "context"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/integrations/GRAPH_EXPORT_ADAPTER_CONSUMER.md"
content_hash: "184b9989a51bcda7ba3558833bc396823d17360254e54c70da3c8fe8ffed7190"
token_cost_estimate: 250
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "auditor"
description: "Unknown"
activation_signals: ["validate", "agent", "contract"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
---
# Graph Export Adapter Consumer Contract

## Consumers

- Graphiti ingestion service
- Neo4j loader
- Hydrator
- CI consistency checks
- Agent memory services

## Consumer rules

1. Treat repo files as source of truth.
2. Treat graph seed as a derived projection.
3. Do not mutate canonical repo text from graph state.
4. Use `source_path` and `content_hash` to resolve and invalidate artifacts.
5. Prefer `sync_graph.py` over direct module calls in automation.

## Expected consumer flow

```text
graph-seed.jsonl
  -> validate
  -> ingest
  -> query by artifact id, type, activation signal, dependency, or source path
  -> hydrator retrieves canonical file body from repo/RAG
```

## Required graph semantics

- `Artifact(id)` nodes are unique.
- `depends_on` edges point from consumer artifact to required artifact.
- `activates_on` edges point from artifact to generated activation-signal nodes.
- Duplicate node ids are invalid in production loaders even if JSONL verification can read them.
