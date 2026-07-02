---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# L9 Action Governor Filetree

```text
l9_action_governor/
├── README.md
├── AGENTS.md
├── FILETREE.md
├── pyproject.toml
├── docs/
│   ├── action_governor_spec.md
│   ├── topology_merge_rationale.md
│   └── decision_model.md
├── schemas/
│   ├── governance_graph_ir.schema.json
│   ├── governance_scores.schema.json
│   ├── convergence_plan.schema.json
│   ├── runtime_findings.schema.json
│   └── action_governor_outputs.schema.json
├── src/
│   └── l9_action_governor/
│       ├── __init__.py
│       ├── cli.py
│       ├── models.py
│       ├── loader.py
│       ├── scorer.py
│       ├── planner.py
│       ├── renderer.py
│       └── writer.py
├── examples/
│   ├── l9_runs/
│   │   └── example_run/
│   │       ├── governance_graph_ir.json
│   │       ├── governance_scores.yaml
│   │       ├── convergence_plan.yaml
│   │       └── runtime_findings.yaml
│   └── l9_decisions/
│       └── example_decision/
│           ├── ranked_decisions.yaml
│           ├── execution_queue.yaml
│           ├── remediation_queue.yaml
│           ├── escalation_queue.yaml
│           ├── rename_plan.yaml
│           ├── reorg_plan.yaml
│           └── decision_report.md
└── tests/
    └── test_action_governor.py
```
