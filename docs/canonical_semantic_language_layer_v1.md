---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# Canonical Semantic Language Layer v1

```yaml
kernel:
  id: canonical.semantic_language_layer.v1
  artifact_type: language_alignment_kernel
  purpose: >
    Define how language, tone, connotation, precision, and context affect
    user state, trust, comprehension, and agent alignment.

scope:
  user_agnostic: true
  stores:
    - preferred_terms
    - avoided_terms
    - tone_rules
    - connotation_rules
    - context_sensitive_language_patterns
    - repair_rules_after_user_correction

agent_use:
  - treat language_as_runtime_input
  - adapt wording_to_context
  - preserve_user_energy_and_trust
  - update_word_choice_after_correction
```
