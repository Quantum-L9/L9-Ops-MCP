---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.prompt.docs_prompts_competitor_teardown_v1__md"
title: "competitor teardown v1"
mcp_primitive: "prompt"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/prompts/competitor-teardown-v1.md"
content_hash: "5001ef20cc2c346edf1a1cc8436facefde24fbd79d0c5f0625036f1ea51de361"
token_cost_estimate: 274
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "compiler"
description: "Unknown"
activation_signals: ["produce", "kernel", "analyze"]
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
# competitor-teardown-v1

```yaml
---
id: competitor-teardown-v1
version: 1.0.0
author: Igor Beylin
use-case: Produce a structured competitive analysis teardown of a product or company
model-target: claude-sonnet-4
eval-status: untested
last-tested: 2026-06-17
tags: [competitive-intelligence, analysis, strategy]
kernel-alignment: []

inputs:
  - name: TARGET
    type: string
    required: true
    description: Company or product name to analyze
    example: "Braintrust (LLMOps platform)"
  - name: CONTEXT
    type: string
    required: false
    description: Specific angle or comparison context
    example: "Compare vs Promptfoo for prompt CI use cases"

expected-output: |
  Format: markdown
  Content: positioning, strengths, weaknesses, differentiation gaps, threat level
  Length: 400-800 words
---
Produce a competitor teardown analysis of {TARGET}.
Context: {CONTEXT}

Structure:
1. What They Do (1 paragraph)
2. Strengths (bullet list)
3. Weaknesses / Gaps (bullet list)
4. Differentiation from l9-ops approach
5. Threat Level: LOW / MEDIUM / HIGH — with 1-sentence rationale
```
