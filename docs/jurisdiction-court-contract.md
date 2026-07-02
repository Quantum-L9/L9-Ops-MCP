---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
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
