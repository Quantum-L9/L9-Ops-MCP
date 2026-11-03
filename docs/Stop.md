---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.context.docs_stop__md"
title: "Stop"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/Stop.md"
content_hash: "1f13009aa567bbd1974bc518e024080134c4003bcbc677b1fe5512d6182c6904"
token_cost_estimate: 232
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "auditor"
description: "Unknown"
activation_signals: ["audit", "check", "validate"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
---
# L9 Stop Hook
## Source: danielmiessler/Personal_AI_Infrastructure#HookSystem.md (Stop event type)

Fires when a playbook execution attempts to terminate.
Acts as the final quality gate — can BLOCK premature exit.

## Gates
1. **All required steps completed?** Check `completed_steps` vs `required_steps` in spec.
   → If incomplete without a valid exit condition: BLOCK with `l9.stop.incomplete_execution`

2. **All required outputs populated?** Validate `$.outputs` against spec output schema.
   → If missing required fields: BLOCK with `l9.stop.missing_outputs`

3. **Audit chain intact?** Verify hash chain for this run's audit records.
   → If chain broken: BLOCK with `l9.stop.audit_chain_broken`

4. **Open compensation actions?** Are any pending saga compensations unresolved?
   → If YES and run_status != `compensated`: BLOCK

5. **ALLOW STOP**: Write final run record to audit log. Update kernel continuity memory.
