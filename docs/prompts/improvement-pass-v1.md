---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.prompt.docs_prompts_improvement_pass_v1__md"
title: "improvement pass v1"
mcp_primitive: "prompt"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/prompts/improvement-pass-v1.md"
content_hash: "899d5e695193cbf2d1a7445ad4d685cee3d94e6c426e73c6bf9b7796a20bb201"
token_cost_estimate: 316
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "meta_kernel_forge"
description: "Unknown"
activation_signals: ["meta", "kernel", "analyze"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
role: "Unknown"
objective: "Unknown"
input_variables: "Unknown"
output_format: "Unknown"
model_target: "claude-sonnet-4"
constraints: "Unknown"
phase_model: "Unknown"
---
# improvement-pass-v1

```yaml
---
id: improvement-pass-v1
version: 1.0.0
author: Igor Beylin
use-case: Run a structured improvement pass on any artifact — identify leverage gaps and prioritize
model-target: claude-sonnet-4
eval-status: untested
last-tested: 2026-06-17
tags: [improvement, meta, self-referential, quality]
kernel-alignment: []

inputs:
  - name: ARTIFACT
    type: string
    required: true
    description: The artifact content or path to analyze
    example: "paste skill YAML or playbook PLAYBOOK.md content"
  - name: FOCUS
    type: string
    required: false
    description: Specific improvement lens
    example: "maximize reusability, harden security surface, reduce token weight"

expected-output: |
  Format: markdown
  Content: hidden leverage, limiting assumptions, double-down recommendations, removal candidates
  Length: 300-600 words
---
Run an improvement pass on the following artifact.
Focus: {FOCUS}

{ARTIFACT}

Structure your output as:
1. Hidden Leverage (underexploited capabilities)
2. Limiting Assumptions (what the artifact assumes that may be wrong)
3. Double Down (what to amplify — with specific evidence)
4. Remove (what to cut — with specific reasoning)
5. Priority Action (single most impactful next move)
```
