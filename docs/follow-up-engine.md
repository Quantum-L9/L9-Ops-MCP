---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# Follow-Up Engine

## Purpose

Track progress, blockers, new unknowns, and follow-up timing. The engine turns a compliance guide into an active execution system instead of a static checklist.

## Matter State

```yaml
matter_state:
  matter_id: string
  matter_type: string
  entity_ref: string
  source_guide_ref: string
  current_phase: string
  overall_status: not_started | active | waiting_on_human | waiting_on_third_party | waiting_on_advisor | ready_for_submission | submitted | confirmed | blocked | closed
  next_best_action: string
  last_run_at: timestamp
  next_follow_up_at: timestamp
```

## Blocker Object

```yaml
blocker:
  blocker_id: string
  matter_id: string
  task_id: string
  blocker_type: missing_credential | missing_document | human_approval_needed | advisor_decision_needed | portal_error | payment_over_threshold | final_submission_gate | ambiguous_source_instruction | third_party_waiting | legal_or_tax_judgment_required | evidence_gap
  severity: low | medium | high | critical
  owner: agent | igor | advisor | third_party
  created_at: timestamp
  next_follow_up_at: timestamp
  resolution_condition: string
  status: open | resolved | stale
```

## Unknown Object

```yaml
unknown:
  unknown_id: string
  matter_id: string
  task_id: string
  question: string
  why_it_matters: string
  needed_from: igor | advisor | portal | agency | document | court | vendor
  blocks_execution: boolean
  deadline_impact: none | low | medium | high
  status: open | answered | no_longer_needed
  follow_up_at: datetime
```

## Follow-Up Triggers

```yaml
follow_up_triggers:
  deadline_based:
    - due_date_minus_14_days
    - due_date_minus_7_days
    - due_date_minus_3_days
    - due_date_minus_1_day
    - due_today
    - overdue

  blocker_based:
    missing_document:
      initial_follow_up: 24h
      repeat_every: 48h
      escalate_after: 5d
    missing_credential:
      initial_follow_up: immediate
      repeat_every: 24h
      escalate_after: 72h
    human_approval_needed:
      initial_follow_up: immediate
      repeat_every: 4h_business_hours
      escalate_after: 24h
    advisor_decision_needed:
      initial_follow_up: 24h
      repeat_every: 72h
      escalate_after: 7d
    third_party_waiting:
      initial_follow_up: 48h
      repeat_every: 72h
      escalate_after: 10d
    portal_error:
      initial_follow_up: immediate
      repeat_every: 24h
      escalate_after: 48h
    evidence_gap:
      initial_follow_up: immediate
      repeat_every: 12h
      escalate_after: 24h
```

## Run Summary

Send a summary only if there is an actionable change:

- task completed
- new blocker
- new unknown
- approval needed
- follow-up due
- evidence gap
- deadline risk
- matter unblocked

Suppress summary when nothing changed.
