---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
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
