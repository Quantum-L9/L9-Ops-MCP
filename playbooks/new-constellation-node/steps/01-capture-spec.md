---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# Step 01 — Capture Node Spec

**Input**: Operator intent (natural language or partial spec)
**Output**: NodeSpec handoff object
**Skill**: None
**Kernels active**: l9_coding_kernel.v1

## Action

1. Collect from operator: node_id, intended actions (list), domain, priority (P0–P3),
   type (worker or orchestrator).
2. Validate node_id matches `^[a-z0-9][a-z0-9-]{0,62}$` — reject if not.
3. Confirm actions list is non-empty.
4. Confirm type is `worker` or `orchestrator`.
5. Construct NodeSpec object (ref: handoffs/node-spec.schema.yaml).

## Validation

NodeSpec object is fully populated with all required fields. No field is None or empty.

## Failure Recovery

If operator cannot supply node_id or actions, stop and request. Do not proceed with
incomplete spec — a bad spec propagates to every subsequent step.

## Handoff

NodeSpec → Step 02 (validate-spec)
