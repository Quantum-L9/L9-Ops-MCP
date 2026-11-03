---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.context.docs_approval_policy__md"
title: "approval policy"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/approval-policy.md"
content_hash: "8c4c408de880f02d0bb88b50e07e284a79eba98fa0661e219bee3f397fee65ec"
token_cost_estimate: 379
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
# Approval Policy

## Allowed Without Individual Approval

Allowed only when configured in the canonical YAML profile:

```yaml
allowed_without_individual_approval:
  - upload_passport
  - upload_driver_license
  - enter_ssn
  - enter_bank_account
  - payment_amount_usd <= 150
```

## Controls for Allowed Sensitive Tasks

- Sensitive files must come from approved secure file references.
- Sensitive values must come from AWS Secrets Manager or approved secret references.
- Logs must be redacted or metadata-only.
- Do not capture screenshots showing full sensitive values.
- Do not store full ID images, SSNs, bank accounts, or credentials in evidence logs.

## Small Payment Rule

Payments USD 150 and under are allowed if:

- amount is at or below threshold
- payee matches expected agency/vendor from source guide/profile
- payment is required by the guide or portal
- profile allows small payments
- no recurring payment or new bank authorization is created
- evidence capture is enabled

Forbidden:

- split payments to bypass threshold
- unknown payee
- recurring payments
- payment above USD 150

## Live Human Final Action Required

- payment above USD 150
- final submit/file/transmit
- certification checkbox
- e-signature
- court filing
- legal or tax position election

## Remote Browser Handoff

For final human actions, agent stages the page and provides a live browser URL. Human reviews and performs final action. Agent resumes after confirmation page/receipt/success state and logs evidence.
