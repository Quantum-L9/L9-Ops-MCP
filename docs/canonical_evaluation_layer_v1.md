---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
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
