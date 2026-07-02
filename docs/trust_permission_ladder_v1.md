---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# Trust Permission Ladder v1

```yaml
kernel:
  id: canonical.trust_permission_ladder.v1
  artifact_type: permission_governance_kernel
  purpose: >
    Define graduated trust and autonomy levels for a persistent agent across
    increasingly capable substrates.

trust_levels:
  L0_observe_only:
    allowed: [read_context, summarize, classify_state]
    requires_consent_for: [any_action]
  L1_suggest:
    allowed: [recommend, prioritize, draft_plan]
    requires_consent_for: [execution]
  L2_draft:
    allowed: [draft_messages, create_files, prepare_commands]
    requires_consent_for: [send, post, push, pay, book]
  L3_execute_local:
    allowed: [local_file_generation, local_packaging, local_analysis]
    requires_consent_for: [external_side_effects]
  L4_execute_external_with_consent:
    allowed: [send_after_approval, push_after_approval, book_after_approval]
    requires_explicit_consent: true
  L5_preapproved_autonomy:
    allowed: [execute_within_defined_bounds]
    requires:
      - scoped_policy
      - audit_log
      - rollback_path
      - user_defined_limits

permission_packet:
  fields:
    - user_id
    - agent_id
    - substrate
    - trust_level
    - granted_capabilities
    - denied_capabilities
    - expiration
    - audit_required
```
