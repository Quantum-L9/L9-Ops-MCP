---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.playbook.playbooks_new_constellation_node_steps_07_verify_health__md"
title: "07 verify health"
mcp_primitive: "tool"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "playbooks/new-constellation-node/steps/07-verify-health.md"
content_hash: "87d7ba196615f3b8fc25700862fe3b1493fc9a28e8e19cfff9aff32363c7ac2a"
token_cost_estimate: 229
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "auditor"
description: "Unknown"
activation_signals: ["check"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
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
