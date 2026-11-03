---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.context.docs_handoff_packet_contract__md"
title: "handoff packet contract"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/handoff-packet-contract.md"
content_hash: "bc5adfd3f801f140a27c38d22935b66b85cbdfd22b23283beff03a71dca28259"
token_cost_estimate: 188
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "builder"
description: "Unknown"
activation_signals: ["create", "agent", "contract"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
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
