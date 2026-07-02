---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# Advisor Guide Parser

## Purpose

Convert advisor-created guides, notices, court orders, permit packets, license renewals, BOI instructions, CPA requests, and agency correspondence into normalized execution objects.

## Extract

- phases and step order
- obligations
- due dates and deadline basis
- agencies, courts, portals, mailing addresses
- credential requirements
- required documents
- forms and attachments
- fees and payment instructions
- signatures, certifications, final submission gates
- evidence and confirmation requirements
- contacts and third parties
- dependencies and blockers
- unknowns and source conflicts

## Rules

- Preserve source instructions.
- Do not convert advisor judgment into agent judgment.
- If the guide says to consult CPA/counsel, mark advisor review required.
- If a deadline is implied but not explicit, mark deadline_basis as inferred and confidence as medium or low.
- If source instructions conflict, create an unknown and blocker.
- Do not invent portal credentials or account IDs.

## Output

Return extracted obligations as draft task nodes using `task-graph-contract.md`.
