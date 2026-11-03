---
id: "L9-Ops-MCP.context.docs_integrations_hydrator_integration__md"
title: "HYDRATOR INTEGRATION"
artifact_type: "context"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/integrations/HYDRATOR_INTEGRATION.md"
content_hash: "56a0ea62c33b2c4c2bb1ff381947c077ed08420c90163a171d1390eaa9c6e49f"
token_cost_estimate: 187
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "research"
description: "Unknown"
activation_signals: ["retrieve"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
---
# Hydrator Integration

## Role

The hydrator uses graph memory to select artifact pointers and then retrieves canonical artifact bodies from the repo/RAG layer.

## Query strategy

1. Query graph for matching activation signals, artifact types, dependencies, and prior decisions.
2. Resolve graph nodes to canonical `source_path`.
3. Retrieve the full artifact body from repo/RAG.
4. Apply context budget and authority rules.
5. Emit `RuntimePayload`.

## Anti-drift rule

The graph may store summaries and relationships, but canonical instructions remain in the repo.

## RuntimePayload fields

Recommended fields:

- `selected_artifacts`
- `artifact_sources`
- `graph_evidence`
- `context_budget`
- `authority_rules`
- `unknowns`
- `trace_id`
