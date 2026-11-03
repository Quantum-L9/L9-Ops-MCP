---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.context.docs_jurisdiction_court_contract__md"
title: "jurisdiction court contract"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/jurisdiction-court-contract.md"
content_hash: "feb0d470e71e8540da84015a4408f0cc506a52cd4aac2155056e511c6c20f23e"
token_cost_estimate: 259
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
# Jurisdiction and Court Contract

## Purpose

Normalize agencies, courts, portals, and jurisdictions across tax, BOI, permits, licenses, annual reports, court deadlines, and private compliance requests.

## Jurisdiction Object

```yaml
jurisdiction:
  level: federal | state | county | municipal | court | private | other
  agency_or_court: string
  jurisdiction: string
  matter: string
  case_or_account_id: string | null
  portal_url: string | null
  filing_method: portal | mail | email | in_person | advisor | unknown
  credential_required: [string]
```

## Court-Specific Fields

```yaml
court:
  court_name: string
  case_number: string
  county: string | null
  state: string | null
  division: string | null
  filing_portal: string | null
  counsel_required: boolean
```

## Rules

- Court filings always require live human/advisor final action.
- Agency filings require live human final action at final submit/certify unless profile grants explicit exception.
- If filing method is unknown, create an unknown and blocker.
