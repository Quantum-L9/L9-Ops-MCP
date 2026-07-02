---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# Step 07 — Verify Health

**Input**: RegistrationResult from Step 06
**Output**: Health check pass confirmation
**Skill**: None
**Kernels active**: l9_coding_kernel.v1

## Action

1. Call `GET http://{node_id}:8000/v1/health`.
2. Confirm response is 200 with `{"status": "healthy"}` (or SDK-defined equivalent).
3. Call Gate node status endpoint (if available): confirm node is active and registered.
4. Send a test packet for each registered action (dry-run if supported).

## Validation

Health endpoint returns 200. Node appears in Gate's node registry.

## Failure Recovery

503 Service Unavailable: Check container is running, GATE_URL is reachable, port is exposed.
200 but status not healthy: Check `engine/boot.py` assertions — one is failing.

## Handoff

PLAYBOOK COMPLETE. Node is registered, healthy, and ready for production traffic.
Document node_id, actions, and internal_url in team node registry.
