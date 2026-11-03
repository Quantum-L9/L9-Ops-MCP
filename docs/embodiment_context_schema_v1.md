---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.context.docs_embodiment_context_schema_v1__md"
title: "embodiment context schema v1"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/embodiment_context_schema_v1.md"
content_hash: "64adb1398ebdfaeb9e1b495821c032ae7515165199da8a6c7ad713183199d6df"
token_cost_estimate: 284
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
# Embodiment Context Schema v1

```yaml
kernel:
  id: canonical.embodiment_context_schema.v1
  artifact_type: embodied_context_kernel
  purpose: >
    Define physical and environmental context fields needed when a persistent
    agent operates through embodied or ambient substrates such as cars, robots,
    wearables, smart homes, and XR.

embodiment_context:
  physical_environment:
    - location_type
    - noise_level
    - light_level
    - motion_state
    - privacy_level
    - people_nearby
    - safety_context
  user_state_if_granted:
    - attention_level
    - interruption_tolerance
    - movement_state
    - schedule_pressure
    - fatigue_or_energy_signal
  substrate_body:
    - mobility
    - manipulation_capability
    - voice_output
    - visual_output
    - sensor_set
    - actuator_set
  action_context:
    - can_interrupt
    - can_move
    - can_modify_environment
    - can_notify_others
    - can_execute_physical_task

agent_rule: >
  Embodied behavior must be context-aware, permission-aware, and low-friction.
  The same agent identity should feel familiar while adapting to the body it occupies.
```
