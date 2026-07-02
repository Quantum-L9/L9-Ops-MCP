---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# Step 06 — Register at Gate

**Input**: CI-passed node from Step 05
**Output**: RegistrationResult handoff object
**Skill**: None
**Kernels active**: l9_coding_kernel.v1

## Action

1. Read `engine/spec.yaml` — confirm node_id, actions, internal_url, priority_class.
2. Execute registration call per Layer 5 contract:
   ```
   POST {GATE_URL}/v1/admin/register?overwrite=true
   Content-Type: application/json
   { "{node-id}": { "internal_url": "http://{node-id}:8000",
     "supported_actions": [...], "priority_class": "P2",
     "max_concurrent": 50, "health_endpoint": "/v1/health", "timeout_ms": 30000 } }
   ```
3. Confirm response is 200 or 201.
4. Construct RegistrationResult: node_id, registered_actions, gate_url, timestamp.

## Validation

Gate returns 200/201. `RegistrationResult.registered_actions` matches NodeSpec.actions.

## Failure Recovery

409 (already exists): Add `?overwrite=true` to request.
400 (bad request): Check supported_actions is non-empty and node_id is lowercase.
404 (gate not found): Confirm GATE_URL env var is correct.

## Handoff

RegistrationResult → Step 07 (verify-health)
