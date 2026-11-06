---
id: "L9-Ops-MCP.playbook.playbooks_new_constellation_node_steps_03_scaffold_node__md"
title: "03 scaffold node"
artifact_type: "playbook"
mcp_primitive: "tool"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "playbooks/new-constellation-node/steps/03-scaffold-node.md"
content_hash: "4249c88ede7fdec94606cdf43bd73177fe700c9e7f21b4343d2d3c19d29653d1"
token_cost_estimate: 227
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "meta_kernel_forge"
description: "Unknown"
activation_signals: ["scaffold", "create", "find"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
---
# Step 03 — Scaffold Node

**Input**: Validated NodeSpec from Step 02
**Output**: ScaffoldResult (created file manifest)
**Skill**: scaffold-node
**Kernels active**: l9_coding_kernel.v1

## Action

1. Load `scaffold-node` skill.
2. Execute scaffold-node skill with the Validated NodeSpec as input.
3. Confirm all Layer 10 required files are created.
4. Confirm L9_META headers present on all files.
5. Confirm `engine/handlers.py` has correct TransportPacket handler signatures.
6. Confirm `engine/spec.yaml` populated from NodeSpec.

## Validation

Run `find {node_id}/ -type f | sort` — compare against Layer 10 required structure.
Every required file present. No missing directories.

## Failure Recovery

If scaffold-node creates incomplete structure, identify missing files and create them
manually following Layer 10 contract.

## Handoff

ScaffoldResult (file manifest) → Step 04 (write-domain-logic)
