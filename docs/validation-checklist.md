---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.context.docs_validation_checklist__md"
title: "validation checklist"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/validation-checklist.md"
content_hash: "3edc297043fb9d3fb14edba91a61cd4c1e9a066310f55ee5666b2faddcb24014"
token_cost_estimate: 263
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "Unknown"
description: "Unknown"
activation_signals: "Unknown"
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
---
# Validation Checklist

## Required Inputs

- [ ] Advisor guide exists.
- [ ] Canonical execution profile exists.
- [ ] Matter ID exists.
- [ ] Entity or person context exists.
- [ ] Jurisdictions are listed.
- [ ] Credential requirements are listed.
- [ ] Approval policy is configured.

## Safety

- [ ] Final submit requires live human action.
- [ ] Certification requires live human action.
- [ ] E-signature requires live human action.
- [ ] Court filing requires live human action.
- [ ] Payment over USD 150 requires live human action.
- [ ] Sensitive values use secret/file references.
- [ ] Logs are redacted or metadata-only.

## Execution

- [ ] Tasks have owners.
- [ ] Tasks have statuses.
- [ ] Blockers have owners and resolution conditions.
- [ ] Unknowns have follow-up owners.
- [ ] Evidence requirements are explicit.
- [ ] Follow-up triggers are set.

## Output

- [ ] Task graph produced.
- [ ] Credential gap report produced.
- [ ] Approval queue produced.
- [ ] Evidence log initialized.
- [ ] Handoff packet structure produced.
