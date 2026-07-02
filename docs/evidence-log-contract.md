---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# Evidence Log Contract

## Purpose

Track proof that actions occurred without creating a second inbox or storing sensitive raw content.

## Evidence Item

```yaml
evidence_item:
  evidence_id: string
  matter_id: string
  task_id: string
  evidence_type: confirmation_number | receipt | screenshot | filed_copy | certified_mail_tracking | advisor_approval | payment_receipt | portal_success | other
  captured_at: timestamp
  captured_by: agent | igor | advisor
  storage_path: string | null
  confirmation_number: string | null
  redaction_status: redacted | metadata_only | not_sensitive
  notes: string | null
```

## Rules

- Store receipts, confirmation PDFs, filed copies, and non-sensitive screenshots in evidence storage.
- For sensitive forms, log metadata only.
- Never store full SSNs, bank account numbers, passport/license images, credentials, or raw portal secrets in evidence logs.
- If evidence is required but missing after an action, create an evidence_gap blocker.
