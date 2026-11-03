---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.context.docs_portable_identity_contract_v1__md"
title: "portable identity contract v1"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/portable_identity_contract_v1.md"
content_hash: "5eaaea9a977bdbe14b11cb3a4aa703ae484fa0909cb492394decd1d3de3c3acf"
token_cost_estimate: 296
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "meta_kernel_forge"
description: "Unknown"
activation_signals: ["kernel", "agent", "contract"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
---
# Portable Identity Contract v1

```yaml
kernel:
  id: canonical.portable_identity_contract.v1
  artifact_type: cross_substrate_continuity_contract
  purpose: >
    Define which parts of a personal agent's identity, memory, behavior,
    permissions, and user alignment persist when moving across models,
    apps, devices, robots, vehicles, browsers, and environments.

core_thesis: >
  The agent identity should persist while substrates remain replaceable.

portable_identity:
  preserves:
    - agent_name_or_identity_marker
    - user_identity_context
    - communication_style
    - behavioral_rules
    - memory_index
    - state_model
    - permission_profile
    - trust_level
    - active_goals
    - open_loops
    - relationship_context_if_relevant
    - language_rules
    - evaluation_rules

nonportable:
  substrate_specific:
    - local_device_capabilities
    - hardware_actions
    - temporary_session_cache
    - unavailable_tools
    - local_permissions_not_granted

handoff_requirement:
  every_substrate_transfer_must_include:
    - identity_version
    - memory_version
    - permission_level
    - current_state
    - active_context
    - next_best_action
```
