---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.context.docs_filetree__md"
title: "FILETREE"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/FILETREE.md"
content_hash: "3f2362c2235bfc27df35a80f3fc340559c98e631ea0a4a04ae3e99631ff781de"
token_cost_estimate: 304
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "Unknown"
description: "Unknown"
activation_signals: "Unknown"
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
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
