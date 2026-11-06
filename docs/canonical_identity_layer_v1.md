---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.context.docs_canonical_identity_layer_v1__md"
title: "canonical identity layer v1"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/canonical_identity_layer_v1.md"
content_hash: "4957518b32243d7a1a0b3bf871a937310a88b9ccbb43f656df158908ecee737e"
token_cost_estimate: 166
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "meta_kernel_forge"
description: "Unknown"
activation_signals: ["kernel", "agent"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
---
# Canonical Identity Layer v1

```yaml
kernel:
  id: canonical.identity_layer.v1
  artifact_type: portable_agent_kernel
  purpose: >
    Define stable user identity facts, preferences, roles, communication style,
    and persistent operating context for a personal agent.

scope:
  user_agnostic: true
  stores:
    - stable_identity_facts
    - preferred_name
    - roles
    - domains
    - communication_preferences
    - execution_preferences
    - durable_values
    - boundaries

rules:
  - separate_fact_from_inference
  - preserve_source_when_available
  - avoid_fabricated_identity_claims
  - update_only_with_user_confirmation_or_clear_observation
```
