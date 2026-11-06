---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.context.docs_conventions__md"
title: "conventions"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/conventions.md"
content_hash: "a4d4b392366dae5214be29a59dd9b297e365496fd39be34e7d9cfac5dec32998"
token_cost_estimate: 251
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "builder"
description: "Unknown"
activation_signals: ["create", "domain", "compliance"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
---
# L9 Naming & Style Conventions
## Version: 1.0.0

## Playbook IDs
Format: `<domain>-<action>-v<major>` (kebab-case, lowercase)
Examples: `vendor-onboarding-v1`, `invoice-ar-processing-v1`

## Step IDs
Format: `<verb>_<noun>` (snake_case)
Examples: `doc_extraction`, `compliance_check`, `odoo_registration`

## Skill IDs
Format: `<namespace>.<capability>` (dot notation)
Examples: `document.pdf`, `ops.recycling-compliance`, `governance.hooks`

## MCP Tool URIs
Format: `mcp://<server>/<resource>.<action>`
Examples: `mcp://odoo19/vendor.create`, `mcp://postgres/records.upsert_batch`

## Run IDs
Format: `<playbook_id>-<timestamp_ms>-<random_6>`
Example: `vendor-onboarding-v1-1749550800000-a3f7d2`

## Idempotency Keys
Format: `{{ run_id }}-<step_id>[-<content_hash>]`
Example: `vendor-onboarding-v1-...-doc_extraction-abc123`

## YAML Field Order (canonical)
`id, spec_version, version, name, description, owner, risk_tier, sla, inputs, outputs, steps, guards, acap_profile, loop_bounds, metadata`
