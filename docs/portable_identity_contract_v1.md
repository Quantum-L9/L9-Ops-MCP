---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
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
