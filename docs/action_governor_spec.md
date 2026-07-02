---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# L9 Action Governor Spec

## Purpose

The Action Governor converts L9 analysis outputs into ranked operational decisions.

It is the layer after topology reconstruction and governance evaluation.

## Required inputs

| File | Purpose |
|---|---|
| `governance_graph_ir.json` | Unified graph of repo artifacts, governance rules, and runtime signals |
| `governance_scores.yaml` | Numeric and categorical assessment of system readiness |
| `convergence_plan.yaml` | Proposed actions from the convergence planner |
| `runtime_findings.yaml` | Live or observed findings, violations, failures, traces, and incidents |

## Required outputs

| File | Purpose |
|---|---|
| `ranked_decisions.yaml` | Master ranked list of all decisions |
| `execution_queue.yaml` | Build and implementation work |
| `remediation_queue.yaml` | Fix, cleanup, canonicalization work |
| `escalation_queue.yaml` | Human-gated blockers, authority conflicts, risk conditions |
| `rename_plan.yaml` | Proposed canonical names |
| `reorg_plan.yaml` | Proposed folder placement and structure |
| `decision_report.md` | Human-readable decision summary |

## Decision packet

Every decision uses this shape:

```yaml
decision_id: string
rank: integer
component_id: string
component_name: string
canonical_name: string
decision_class: build_now | build_next | build_later | remediate_now | escalate | rename | reorganize | archive | delete | defer
priority_score: integer
confidence: high | medium | low
reason: string
next_action: string
evidence: []
dependencies: []
risks: []
target_folder: string
approval_required: boolean
```

## Scoring model

```text
priority_score =
  strategic_value * 2.0
+ governance_criticality * 1.7
+ reuse_potential * 1.4
+ implementation_readiness * 1.2
+ runtime_urgency * 1.6
+ convergence_leverage * 1.5
- entropy_penalty * 1.3
- dependency_blockers * 1.4
```

Scores are normalized to 0-100.

## Decision class rules

| Condition | Decision |
|---|---|
| high strategic value + high readiness + low blockers | `build_now` |
| high strategic value + medium readiness | `build_next` |
| high value + high blockers | `escalate` |
| low value + high entropy | `archive` |
| duplicate + no unique capability | `delete` |
| naming drift only | `rename` |
| misplaced component | `reorganize` |
| runtime failure + governed component | `remediate_now` |
| insufficient evidence | `defer` |

## Safety posture

The MVP is proposal-only.

The Action Governor may produce plans, not mutate files.
