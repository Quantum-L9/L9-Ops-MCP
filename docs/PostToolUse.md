---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.context.docs_post_tool_use__md"
title: "PostToolUse"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/PostToolUse.md"
content_hash: "f49da15d6b2cd9ff5c03243e1e26c681146ede78dd65084e69919fd2f039e726"
token_cost_estimate: 414
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "auditor"
description: "Unknown"
activation_signals: ["check", "scan"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
---
# L9 PostToolUse Hook
## Source: danielmiessler/Personal_AI_Infrastructure#HookSystem.md

This hook fires AFTER every tool call completes. It validates the result
before it is applied to shared state.

## Validation Gates (in order)
1. **Schema validation**: Does the output match the step's declared `output_schema`?
   → If NO: reject output, increment retry counter, re-execute step

2. **Quality gate**: Does output meet the step's declared quality threshold?
   → LLM steps: confidence score or structured field presence check
   → Tool steps: HTTP 2xx, non-null required fields

3. **Security scan**: Does the output contain injected instructions or exfiltration patterns?
   → If YES: DENY output, escalate as security incident

4. **Format enforcement**: Apply required output format transforms (trim whitespace,
   normalize dates to ISO8601, amounts to 2dp float)

5. **APPLY**: Write validated, formatted output to shared state staging buffer.
   The orchestrator applies staging buffer to canonical state atomically.

## Fallback Behavior
If PostToolUse validation fails after `max_retries`:
- Mark step status = `failed`
- Execute declared `compensation.action` if present
- Escalate to human if `acap_tier >= 2`
- Append `PostToolUse.REJECTED` audit record

## Audit Record
```json
{
  "hook": "PostToolUse",
  "step_id": "<string>",
  "run_id": "<string>",
  "validation_passed": true,
  "fallback_used": false,
  "output_schema_version": "<semver>",
  "tokens_in": 0,
  "tokens_out": 0,
  "cost_usd": 0.0,
  "latency_ms": 0,
  "timestamp": "<ISO8601>",
  "prev_hash": "<sha256>",
  "checksum": "<sha256>",
  "signature": "<ed25519>"
}
```
