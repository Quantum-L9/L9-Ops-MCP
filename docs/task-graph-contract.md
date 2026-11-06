---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.context.docs_task_graph_contract__md"
title: "task graph contract"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/task-graph-contract.md"
content_hash: "0fac7e7aec465b2ff3f74f4bfb6be219877ba4cef25a908d2b324e6512ff81ae"
token_cost_estimate: 417
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "domain_agent"
description: "Unknown"
activation_signals: ["agent", "contract"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
---
# Task Graph Contract

## Task Node

```yaml
task_node:
  task_id: string
  matter_id: string
  source_phase: string
  source_reference: string
  action_type: collect_document | fill_form | upload_file | enter_secret | pay_fee | draft_message | call_vendor | submit_filing | certify | wait_for_response | log_confirmation | advisor_review | human_review
  title: string
  owner: agent | igor | advisor | vendor | agency | court | third_party
  status: not_started | in_progress | waiting_on_credential | waiting_on_document | waiting_on_human_approval | waiting_on_third_party | waiting_on_advisor | ready | done | blocked | cancelled
  due_date: date | null
  follow_up_at: datetime | null
  follow_up_rule: string | null
  blocker_reason: string | null
  unknowns: [string]
  credential_required: [string]
  evidence_required: [confirmation_number | receipt | screenshot | filed_copy | tracking_number | advisor_approval]
  approval_gate:
    required: boolean
    reason: string | null
  automation_allowed:
    allowed: boolean
    reason: string
```

## Relationships

```yaml
relationships:
  - Matter HAS_TASK Task
  - Task DEPENDS_ON Task
  - Task BLOCKED_BY Blocker
  - Task HAS_UNKNOWN Unknown
  - Task REQUIRES_CREDENTIAL CredentialRequirement
  - Task PRODUCES_EVIDENCE EvidenceItem
```

## Status Rules

- A task with unmet credential requirements is `waiting_on_credential`.
- A task with missing source documents is `waiting_on_document`.
- A task at final submit/certify/e-sign/payment-over-threshold is `waiting_on_human_approval`.
- A task waiting for CPA/counsel is `waiting_on_advisor`.
- A task with source conflict is `blocked` until resolved.
