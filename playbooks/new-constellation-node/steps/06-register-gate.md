---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.playbook.playbooks_new_constellation_node_steps_06_register_gate__md"
title: "06 register gate"
mcp_primitive: "tool"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "playbooks/new-constellation-node/steps/06-register-gate.md"
content_hash: "6dd333c8d1ba09cce6a6573752c4bcd01c9d3fc8c596a10a0bcee2a08304bcae"
token_cost_estimate: 280
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "builder"
description: "Unknown"
activation_signals: ["construct", "contract"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
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
