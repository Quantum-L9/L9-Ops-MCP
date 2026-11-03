---
id: "L9-Ops-MCP.context.docs_integrations_graph_export_adapter__md"
title: "GRAPH EXPORT ADAPTER"
artifact_type: "context"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/integrations/GRAPH_EXPORT_ADAPTER.md"
content_hash: "5267f810c6deee6052ceaa0ce4e2993c40e83f083ddc437e3e6922f37ab9181c"
token_cost_estimate: 226
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "Unknown"
description: "Unknown"
activation_signals: "Unknown"
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
---
# Graph Export Adapter

## Purpose

Exports V2 metadata/retrieval indexes into `graph-seed.jsonl`.

## Input

A JSON index containing artifact objects. Supported top-level layouts:

- list of objects
- `{ "artifacts": [...] }`
- `{ "items": [...] }`
- `{ "records": [...] }`
- `{ "documents": [...] }`
- `{ "resources": [...] }`

## Output

JSONL records:

- `artifact_node`
- `artifact_edge`

## Mapping

| V2 field | Graph field |
|---|---|
| `id` / `artifact_id` | `artifact.id` |
| `artifact_type` / `type` | `artifact.artifact_type` |
| `source_path` / `path` / `file` | `artifact.source_path` |
| `retrieval_keys` / `activation_signals` / `tags` | `artifact.activation_signals` |
| `dependencies` / `depends_on` / `requires` | dependency edges |

## Failure behavior

The adapter fails closed for missing required node fields, invalid JSON, unsupported records, and malformed callable metadata.
