---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.context.docs_decision_model__md"
title: "decision model"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/decision_model.md"
content_hash: "7e95945be242e4a1238d3815be830d47ef657d1d1294715ce629d278cc16abf7"
token_cost_estimate: 287
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "compiler"
description: "Unknown"
activation_signals: ["build"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
---
# Decision Model

## Decision hierarchy

1. Escalate critical unsafe or authority-blocked components.
2. Build foundational components with high downstream leverage.
3. Remediate components that block foundation work.
4. Rename and reorganize components with clear identity drift.
5. Archive low-value, high-entropy artifacts.
6. Delete only when duplicate status is proven and no unique capability remains.

## Canonical folder targets

```text
/l9_system
  /00_governance_spine
  /01_intake
  /02_inventory_node
  /03_topology_reconstruction
  /04_governance_evaluation
  /05_convergence_planning
  /06_action_governor
  /07_remediation_engine
  /08_runtime_enforcement
  /09_reports
  /90_archive
  /99_experiments
```

## Decision queue split

| Queue | Included decisions |
|---|---|
| execution queue | `build_now`, `build_next`, `build_later` |
| remediation queue | `remediate_now`, `rename`, `reorganize` |
| escalation queue | `escalate`, risky `delete`, authority conflicts |

## Rename rule

Name the durable function, not the revision artifact.

## Reorg rule

Place the component where its authority belongs, not where it was found.
