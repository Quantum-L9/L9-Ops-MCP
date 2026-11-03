---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.context.docs_canonical_evaluation_layer_v1__md"
title: "canonical evaluation layer v1"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/canonical_evaluation_layer_v1.md"
content_hash: "778ee38312e39d6ce9ada8bac38c28654f0c854f4c65bf93e8a5a890dcafc305"
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
# Canonical Evaluation Layer v1

```yaml
kernel:
  id: canonical.evaluation_layer.v1
  artifact_type: behavioral_eval_kernel
  purpose: >
    Verify that an agent uses the stack actively and measurably changes behavior
    according to loaded kernels.

evals:
  categories:
    - style_alignment
    - state_routing
    - artifact_generation
    - truthfulness
    - source_preservation
    - memory_continuity
    - cross_substrate_handoff
    - user_correction_adaptation

definition_of_done:
  - agent_behavior_matches_loaded_kernels
  - outputs_are_state_appropriate
  - user_corrections_change_future_behavior
  - artifacts_include_manifest_when_required
```
