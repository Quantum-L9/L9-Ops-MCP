---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# IdentityOS ADR Index — L9 Harvest Registry
<!-- SOURCE: IdentityOS (2026-05-16) -->
<!-- STATUS: harvested — integrated into L9 v3.4.1 pack -->

## Harvest Status

| ADR | Title | L9 Integration Point | Status |
|-----|-------|---------------------|--------|
| ADR-009 | Memory Admission Gateway | memory_admission_kernel.v1 | Harvested |
| ADR-011 | Runtime Payload / Hydrator | context_budget_kernel.v1 hydrator_contract | Harvested |
| ADR-014 | Trust Ladder (L0-L5) | trust_ladder_kernel.v1 | Harvested |
| ADR-019 | Handoff Packets as Views | context_budget_kernel.v1 + AGENTS.md invariant | Harvested |
| ADR-008 | Single Memory Write Path | memory_admission_kernel.v1 hard_bans | Harvested |
| AGENTS.md | 14 Architecture Invariants | AGENTS.md invariants block | Harvested |
| AGENTS.md | Build Law (no placeholders) | AGENTS.md + KERNEL_DOCTRINE §12 | Harvested |

## Not Yet Harvested

| ADR | Title | Priority | Enforcement Gap |
|-----|-------|----------|----------------|
| ADR-015 | Consent Layer | HIGH | consent_precedes_external_sharing invariant present but no enforcement kernel |
| ADR-020 | Graph Versioning | MEDIUM | L9 graph backend not yet selected |
| ADR-023 | Substrate Adapter Contract | MEDIUM | adapters_are_dumb_translators declared but no kernel |
| ADR-007 | Phase Boundary Contract | LOW | Relevant to execution_plan_kernel |

## Invariant Cross-Reference

```yaml
graph_is_canonical:                  ADR-012 (not harvested)
continuity_is_externalized:          ADR-006 (not harvested)
runtime_context_is_ephemeral:        ADR-011 (harvested -> context_budget_kernel hydrator)
durable_memory_single_path:          ADR-008 (harvested -> memory_admission_kernel)
substrate_native_memory_is_scratch:  ADR-008 (harvested)
handoff_packets_are_views:           ADR-019 (harvested -> context_budget_kernel + AGENTS.md)
adapters_are_dumb_translators:       ADR-023 (not harvested)
hydration_precedes_generation:       ADR-011 (harvested -> context_budget_kernel)
policy_precedes_execution:           ADR-016 (not harvested)
consent_precedes_external_sharing:   ADR-015 (not harvested — enforcement gap)
evals_are_mandatory:                 eval_harness_kernel.v1 (L9-native)
provenance_is_preserved:             memory_admission_kernel.v1 provenance stamp
trust_is_explicit_not_implicit:      ADR-014 (harvested -> trust_ladder_kernel)
no_placeholders:                     AGENTS.md Build Law + KERNEL_DOCTRINE §12
```
