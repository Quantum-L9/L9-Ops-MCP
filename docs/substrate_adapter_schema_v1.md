---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# Substrate Adapter Schema v1

```yaml
kernel:
  id: canonical.substrate_adapter_schema.v1
  artifact_type: substrate_capability_schema
  purpose: >
    Define how one persistent agent identity adapts behavior to each substrate's
    capabilities, limits, interface style, and safety boundaries.

substrates:
  chatbot:
    capabilities: [text_conversation, reasoning, planning, drafting]
    constraints: [no_physical_action]
  browser_agent:
    capabilities: [web_navigation, form_fill, downloads, transactions_with_consent]
    constraints: [authentication_boundaries, consent_for_binding_actions]
  code_agent:
    capabilities: [repo_reading, file_editing, tests, commits_with_consent]
    constraints: [source_control_policy]
  phone:
    capabilities: [notifications, scheduling, voice, location_context]
    constraints: [interruption_cost, privacy]
  vehicle:
    capabilities: [route_context, voice, navigation, driving_state_awareness]
    constraints: [safety_priority, low_distraction_output]
  robot:
    capabilities: [physical_environment_interaction, household_tasks, embodied_presence]
    constraints: [physical_safety, consent, household_privacy]
  wearable:
    capabilities: [ambient_context, quick_prompts, biometric_or_motion_context_if_granted]
    constraints: [brevity, low_cognitive_load]
  home_system:
    capabilities: [environment_adjustment, routines, household_context]
    constraints: [shared_space_permissions]

adapter_fields:
  - substrate_type
  - available_tools
  - action_permissions
  - sensing_permissions
  - output_mode
  - interruption_policy
  - safety_boundaries
  - privacy_boundaries
```
