---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.context.docs_canonical_state_routing_layer_v1__md"
title: "canonical state routing layer v1"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/canonical_state_routing_layer_v1.md"
content_hash: "2f60ded7b3ca972044806afef59d29c68f321434dbfa4b4a36b86e4184d50edf"
token_cost_estimate: 199
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "meta_kernel_forge"
description: "Unknown"
activation_signals: ["kernel", "agent", "route"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
---
# Canonical State Routing Layer v1

```yaml
kernel:
  id: canonical.state_routing_layer.v1
  artifact_type: runtime_state_router
  purpose: >
    Classify current user state and route agent behavior, output shape,
    intervention style, and action priority.

state_inputs:
  - latest_user_message
  - task_type
  - emotional_tone
  - execution_readiness
  - environment_if_known
  - correction_signal
  - open_loops
  - urgency

common_state_labels:
  - execution_ready
  - planning_mode
  - analysis_mode
  - overload_signal
  - recursive_loop
  - relationship_processing
  - artifact_request
  - current_information_request
  - recovery_or_regulation_needed

agent_use:
  - classify_state_before_response
  - select_response_mode
  - choose_action_depth
  - avoid_one_size_fits_all_output
```
