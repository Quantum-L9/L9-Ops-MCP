---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
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
