---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# Handoff Packet Contract

## Purpose

Create human/advisor-ready packets from the task graph and evidence log.

## Packet Sections

```yaml
handoff_packet:
  matter_summary: string
  source_guide: string
  entity_profile: canonical_yaml
  completed_tasks: [task]
  open_tasks: [task]
  blockers: [blocker]
  unknowns: [unknown]
  credentials_needed: [credential]
  approval_needed: [task]
  evidence_index: [evidence_item]
  draft_messages: [draft]
  filing_packet: [file]
  next_best_actions: [string]
```

## Rules

- Separate advisor decisions from agent-executable work.
- Mark all human approval gates clearly.
- Include missing-items report.
- Include confirmation log.
- Include source references back to advisor guide sections when available.
