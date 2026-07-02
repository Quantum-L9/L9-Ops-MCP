---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# Step 02 — Validate Node Spec

**Input**: NodeSpec from Step 01
**Output**: Validated NodeSpec
**Skill**: None
**Kernels active**: l9_coding_kernel.v1

## Action

1. Check node_id: lowercase, hyphenated, matches regex `^[a-z0-9][a-z0-9-]{0,62}$`.
2. Check each action: lowercase, matches `^[a-z0-9][a-z0-9-]{0,63}$`.
3. Check priority_class: P0, P1, P2, or P3.
4. Check type: worker or orchestrator.
5. Check domain: non-empty string.
6. If any check fails: return error with specific field and rule violated.

## Validation

All fields pass regex and enum checks. Report PASS for each field.

## Failure Recovery

Return FAIL with specific field(s) that failed. Request operator to correct.
Do not proceed to scaffold with invalid spec.

## Handoff

Validated NodeSpec → Step 03 (scaffold-node)
