---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# Canonical Identity Layer v1

```yaml
kernel:
  id: canonical.identity_layer.v1
  artifact_type: portable_agent_kernel
  purpose: >
    Define stable user identity facts, preferences, roles, communication style,
    and persistent operating context for a personal agent.

scope:
  user_agnostic: true
  stores:
    - stable_identity_facts
    - preferred_name
    - roles
    - domains
    - communication_preferences
    - execution_preferences
    - durable_values
    - boundaries

rules:
  - separate_fact_from_inference
  - preserve_source_when_available
  - avoid_fabricated_identity_claims
  - update_only_with_user_confirmation_or_clear_observation
```
