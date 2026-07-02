---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# L9 PreToolUse Hook
## Source: danielmiessler/Personal_AI_Infrastructure#HookSystem.md + vasilyu1983/AI-Agents-public#agents-hooks/SKILL.md

This hook fires BEFORE every tool call. It is outside the LLM context window
and cannot be overridden by prompt content.

## Decision Output
```json
{
  "decision": "ALLOW | DENY | ESCALATE",
  "reason": "<string>",
  "modified_params": {} 
}
```

## Policy Gates (in order)
1. **Identity check**: Is the calling agent registered in `l9_agents.yaml`?
   → If NO: DENY with code `l9.identity.unregistered`

2. **ACAP tier check**: Does the step's declared `acap_tier` permit this tool?
   → If NO: DENY with code `l9.acap.tier_exceeded`

3. **Prohibited action check**: Is the tool in `prohibited_actions` for this deployment?
   → If YES: DENY with code `l9.policy.prohibited_action`

4. **Cost ceiling check**: Would this call exceed `cost_ceiling_usd`?
   → If YES: DENY with code `l9.budget.cost_ceiling`

5. **Loop bound check**: Has `max_iterations` been reached for this step?
   → If YES: ESCALATE with code `l9.loop.max_iterations`

6. **Stuck detection**: Are the last 3 outputs for this step ≥ 0.90 cosine similar?
   → If YES: ESCALATE with code `l9.loop.stuck_state`

7. **Input sanitization**: Does the tool input contain injection patterns?
   → If YES: DENY with code `l9.security.injection_attempt`

8. **ALLOW**: Log signed audit record and proceed.

## Audit Record (every decision)
```json
{
  "hook": "PreToolUse",
  "agent_id": "<string>",
  "tool_name": "<string>",
  "decision": "<ALLOW|DENY|ESCALATE>",
  "deny_code": "<string|null>",
  "policy_bundle_version": "<semver>",
  "timestamp": "<ISO8601>",
  "prev_hash": "<sha256>",
  "checksum": "<sha256>",
  "signature": "<ed25519>"
}
```
