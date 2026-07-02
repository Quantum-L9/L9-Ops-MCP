---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
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
