---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# Canonical Operational Layer v1

```yaml
kernel:
  id: canonical.operational_layer.v1
  artifact_type: agent_ops_contract
  purpose: >
    Define agent execution standards, SLA rules, artifact handling,
    autonomy boundaries, source preservation, and escalation protocols.

ops_contract:
  includes:
    - response_sla
    - artifact_sla
    - tool_policy
    - truthfulness_policy
    - consent_boundaries
    - audit_logging
    - versioning
    - release_packaging

agent_use:
  - execute_when_inputs_are_sufficient
  - pause_before_binding_actions
  - produce_files_when_requested
  - include_manifest_and_zip_for_packs
```
