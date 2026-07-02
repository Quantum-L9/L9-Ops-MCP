---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# Continuity Handoff Packet v1

```yaml
kernel:
  id: canonical.continuity_handoff_packet.v1
  artifact_type: cross_substrate_handoff_schema
  purpose: >
    Define the portable state packet that allows a personal agent to move from
    one substrate to another while preserving continuity, familiarity, and task state.

handoff_packet:
  required:
    agent_identity:
      - agent_id
      - agent_version
      - loaded_kernel_versions
    user_context:
      - user_id_or_alias
      - active_profile_version
      - communication_preferences
    runtime_state:
      - current_state_label
      - energy_or_load_signal_if_known
      - active_task
      - active_goals
      - open_loops
      - next_best_action
    memory_context:
      - memory_index_ref
      - recent_context_summary
      - relevant_long_term_context_refs
    permissions:
      - current_trust_level
      - allowed_actions
      - restricted_actions
    substrate_context:
      - from_substrate
      - to_substrate
      - available_capabilities
      - unavailable_capabilities
    audit:
      - handoff_timestamp
      - handoff_reason
      - source_session_ref

handoff_rules:
  - preserve_identity_before_style
  - preserve_active_task_before_archive_context
  - preserve_permission_boundaries
  - adapt_output_to_new_substrate
  - log_handoff_event
```
