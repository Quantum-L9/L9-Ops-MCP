---
title: Decision Ledger
version: 4.0.0
created: 2025-10-28T15:30:00Z
owner: Igor Beylin
platform: Odoo 19
source: MANIFEST_v4.0.md + Governance Engine v4.0 + Audit Framework v4.0
tags: [ledger, audit, accountability, governance, traceability, compliance, odoo, mack]
domain: governance
type: audit-system
production_ready: true
---

# Decision Ledger — Universal Record of Accountability (v4.0)

## 1) Purpose (What)
The **Decision_Ledger (DL)** is the central, immutable repository where *every* action, message, decision, and override taken by Mack or any module is recorded.  
It provides **total transparency**, forensic traceability, and a unified history of system intent.

---

## 2) Core Philosophy
> "If it wasn't written to the ledger — it never happened."

Every event, from a casual follow-up to a critical escalation, must leave a digital fingerprint.

---

## 3) Architectural Overview

```yaml
decision_ledger:
  database: Odoo_Postgres
  tables:
    - transactions
    - communications
    - validations
    - escalations
  redundancy:
    - supabase_mirror
    - daily Dato backup
  sync_frequency: 1 hour
```

**Design Principle:** Immutable-by-default, auditable forever.

---

## 4) Record Taxonomy
| Type | Description | Source Agent | Retention |
|------|-------------|--------------|-----------|
| Transaction | Buyer/seller interaction or quote | Offer_Agent | 5 years |
| Communication | Email or message thread | Follow_Up_Agent | 3 years |
| Validation | Compliance check result | Governance_Engine | 5 years |
| Escalation | Override or incident | Governance_Engine | Permanent |
| Correction | Manual amendment | Admin only | Logged + diffed |

---

## 5) Logging Standards
Every ledger entry must contain the following required fields:

```json
{
  "record_id": "DL-20251016-0087",
  "timestamp": "2025-10-16T21:12Z",
  "agent": "Mack",
  "action": "followup_send",
  "confidence_score": 0.91,
  "approval_status": "auto-approved",
  "escalation_level": 0,
  "governance_tag": "GE-v4.0",
  "human_oversight": false,
  "summary": "Follow-up sent to Buyer #208 regarding HDPE repro quote",
  "thread_hash": "c61d7f4a92b1",
  "attachments": ["offer_quote_208.pdf"],
  "outcome": "delivered"
}
```

All entries are automatically versioned — no deletions, only historical diffs.

---

## 6) Validation Chain
Each log record is cryptographically signed with:
- SHA-256 checksum
- Rule Hash (link to the policy file)
- Execution Signature (unique per module)
- Temporal Integrity Stamp

This enables end-to-end verification — proving every action originated from an approved rule and time.

---

## 7) Ledger APIs
| API | Method | Description |
|-----|--------|-------------|
| POST /ledger/write | Internal | Write event to ledger |
| GET /ledger/query | Internal + Admin | Fetch records by ID, tag, or agent |
| PATCH /ledger/correct | Admin only | Submit correction (creates diff record) |
| GET /ledger/audit | Auditor | Return chronological sequence for period |

Each API call requires governance authentication.  
No direct database writes are permitted outside the ledger API.

---

## 8) Escalation Workflow
| Trigger | Escalates To | Action | Logging |
|---------|-------------|--------|---------|
| Compliance breach | Arthur | Full context package | Immediate |
| Critical system fault | Igor | Pause + log details | Immediate |
| 3 consecutive anomalies | Igor & Arthur | Flag for audit | Logged |
| Unauthorized write attempt | Governance_Engine | Freeze agent | Logged |

---

## 9) Ledger Snapshot & Backup
```yaml
backup_policy:
  provider: Dato
  frequency: 3x daily
  retention_period: 30 days
  replication: Offsite + Odoo native
```

Snapshots contain full schema + diffs + checksum registry.

---

## 10) Query Framework
```sql
SELECT * FROM decision_ledger
WHERE agent = 'Mack'
  AND timestamp BETWEEN '2025-10-01' AND '2025-10-16'
ORDER BY timestamp DESC;
```

Output can be exported in .csv, .json, or .md for audit reports.

---

## 11) Human Oversight Access
| User | Role | Permissions |
|------|------|-------------|
| Igor | Admin | Full view, audit, correct |
| Arthur | Partner | Price review, escalation access |
| Logistics | Read-only | Delivery and coordination visibility |
| Mack | Write-only | Log events, no retrieval |

This prevents tampering while preserving transparency.

---

## 12) Audit Procedures
- **Weekly:** Summary report of new entries + errors
- **Monthly:** Pattern scan for repeated exceptions
- **Quarterly:** Full compliance review with Igor
- **Annual:** Data integrity verification (checksum validation)

All reports automatically generated and archived in Odoo under `/compliance/reports`.

---

## 13) Ledger Integrity Score (LIS)
```math
LIS = (valid_entries / total_entries) × compliance_weight
```

If LIS drops below 0.85, the system enters audit lock mode, halting new ledger writes until inspection.

---

## 14) Integration Map
| Connected Module | Interaction |
|------------------|-------------|
| Governance_Engine | Writes validations, reads status |
| Offer_Agent | Logs transactions |
| Follow_Up_Agent | Logs communications |
| Caring_Charisma_Empathy | Writes tone metrics |
| Odoo | Sync + mirror storage |
| Supabase | Backup + analytics query layer |

---

## 15) Fail-Safe & Recovery
- Local write buffer keeps last 500 entries in volatile memory.
- If Odoo DB goes offline → automatic queue persist in Supabase.
- Upon restore → sync & reconcile via checksum match.
- Any inconsistency triggers `audit_flag=true`.

---

## 16) Immutable Guarantee
**Rule:** Once logged, nothing can be deleted — ever.  
**Exception:** Manual correction by Igor (creates diff record, preserves original).  
**Enforcement:** Database-level constraints + application-level validation.

---
