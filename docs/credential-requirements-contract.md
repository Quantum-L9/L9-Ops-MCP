---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.context.docs_credential_requirements_contract__md"
title: "credential requirements contract"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/credential-requirements-contract.md"
content_hash: "820ade4d0b88ceeb72a19b062e7eabb4d528fe7d4437618f43298c3268b08e7d"
token_cost_estimate: 284
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "legal"
description: "Unknown"
activation_signals: ["contract", "compliance"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
---
# Credential Requirements Contract

## Purpose

Define every portal, secret, secure file, payment method, and MFA requirement needed to execute a matter.

## Credential Object

```yaml
credential:
  credential_name: string
  credential_type: portal_login | secret_value | secure_file | api_key | payment_method | mfa | other
  access_target: string
  jurisdiction: string
  portal_url: string | null
  aws_secret_name: string
  mfa_required: boolean
  human_only: boolean
  allowed_use:
    - login
    - fill_form_field
    - upload_to_portal
    - payment_under_threshold
    - retrieve_document
  log_policy: metadata_only | redacted_only | no_log
```

## AWS Naming Pattern

```yaml
aws_secret_name: compliance/{{entity_slug}}/{{credential_name}}
```

For person-level sensitive values:

```yaml
aws_secret_name: compliance/people/{{person_slug}}/{{credential_name}}
```

## Gap Handling

If a credential is missing, create a blocker:

```yaml
blocker_type: missing_credential
owner: igor
severity: high if deadline <= 7 days else medium
resolution_condition: "Add secret to AWS Secrets Manager and mark credential available."
```
