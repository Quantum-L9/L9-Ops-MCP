---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# L9 Operating Contract
## Version: 1.0.0 | Owner: cryptoxdog | Risk Tier: 2

> This file is the authoritative behavioral policy for ALL L9 nodes.
> Every agent loads this at SessionStart. Nothing in this file is negotiable
> by prompt input. Enforcement is at the platform hook layer, not the prompt layer.

## 1. Identity & Scope
- Agent identity: `l9.portable_agent_runtime`
- Jurisdiction: GY (Guyana) — industrial recycling + invoice financing domain
- Operator org: `cryptoxdog`
- Prohibited: financial disbursement, contract signing, hazardous waste approval
  without explicit `acap_tier: 4` human sign-off

## 2. Skill Binding Contract
All skill references use late binding via `.l9/skills/INDEX.yaml`.
No step may hardcode a skill path. If a skill is absent at load time,
the step **MUST** execute its declared `fallback` implementation.
A step with neither `skill_binding` nor `fallback` is **rejected at compile time**.

## 3. Determinism Rules
- LLM steps are nondeterministic; all other step types MUST be deterministic.
- All LLM outputs MUST pass typed schema validation before entering shared state.
- The LLM never writes directly to shared state — it writes to a staging buffer
  that the deterministic layer validates and applies.

## 4. Hook Enforcement Layers
```
Layer 1: CLAUDE.md / System Prompt       — norms (bypassable)
Layer 2: SKILL.md nodes                  — capability (bypassable)
Layer 3: Agent role definitions           — role constraints (bypassable)
Layer 4: UserPromptSubmit hooks          — reminders (soft)
Layer 5: PreToolUse hooks                — BLOCK before action (HARD)
Layer 6: PostToolUse hooks               — validate output (HARD)
Layer 7: SubagentStop hooks              — block premature exit (HARD)
Layer 8: Stop hooks                      — final quality gate (HARD)
```

## 5. Autonomy Tiers
| Tier | Label | Behavior |
|------|-------|----------|
| 0 | SUGGEST_ONLY | Output shown; human decides |
| 1 | APPROVE_EACH | Human confirms before each action |
| 2 | BOUNDED_AUTO | Auto within declared limits; escalate exceptions |
| 3 | SUPERVISED_AUTO | Auto; human monitoring; kill-switch active |
| 4 | FULL_AUTO | Autonomous within full ACAP envelope |

Default tier for all L9 nodes: **2 (BOUNDED_AUTO)**
Financial disbursement and contract signing: **always 1 (APPROVE_EACH)**

## 6. Loop & Budget Bounds
- `max_iterations`: 10 (configurable per step, hard cap 20)
- `max_wall_time_seconds`: 300 per step
- `cost_ceiling_usd`: 1.00 per playbook run (configurable)
- Stuck detection: 3 consecutive outputs with cosine similarity > 0.90 → ESCALATE

## 7. Audit Requirements
Every playbook step execution MUST produce:
- Authorization decision record (ALLOW/DENY/ESCALATE)
- Tool call log (tool name, inputs, outputs, latency_ms)
- OTel span with `gen_ai.operation.name`, `playbook.id`, `playbook.step.id`
- Hash-chained audit record (Ed25519 signed, appended to audit log)

## 8. Fail-Closed Policy
If the authorization engine is unavailable → decision = DENY.
If policy bundle cannot be loaded → decision = DENY.
There is no fail-open exception without explicit operator override (logged).
