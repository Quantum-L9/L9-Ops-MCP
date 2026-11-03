---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.playbook.playbooks_new_constellation_node_steps_02_validate_spec__md"
title: "02 validate spec"
mcp_primitive: "tool"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "playbooks/new-constellation-node/steps/02-validate-spec.md"
content_hash: "16243e039484ea5c119c7f8bf3fbbde860c2775fdc654682c81ee4068dfae0b6"
token_cost_estimate: 200
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "auditor"
description: "Unknown"
activation_signals: ["check", "validate", "scaffold", "domain"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
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
