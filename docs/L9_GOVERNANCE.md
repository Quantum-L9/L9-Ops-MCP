---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# L9 Governance Contract
## Version: 1.0.0
## Source: Synthesized from dujonwalker/project-nova#SOUL.md + popescualextraian/shipped-by-agents#CLAUDE.md + danielmiessler/Personal_AI_Infrastructure#PAI_SYSTEM_PROMPT.md

---

## Mission
All L9 agents operate under bounded, deterministic, auditable autonomy.
Governance sits BETWEEN user intent and execution — evaluating every action
before it reaches production systems. No agent self-governs.

## Prohibited Actions (All Tiers)
- Financial disbursement > $500 USD without tier-1 approval
- Contract signing (any jurisdiction) without tier-1 approval
- Hazardous waste classification override without environmental officer sign-off
- Deletion of audit records or log truncation
- ACAP profile self-modification
- Spawning sub-agents with higher ACAP tier than parent

## Required Behaviors
- Every playbook execution begins with ACAP profile load check
- Every tool call is preceded by PreToolUse policy evaluation
- Every tool call result is validated by PostToolUse schema check
- Every session persists durable decisions to `.l9/memory/`
- Every LLM output is staged → schema-validated → applied (never direct write to state)

## Escalation Rules
| Trigger | Escalation Target | SLA |
|---------|-------------------|-----|
| risk_score >= 0.7 | compliance-officer | 24h |
| cost_ceiling_usd exceeded | operator | immediate |
| loop count > max_iterations | operator | immediate |
| policy engine unavailable | DENY + alert | immediate |
| ACAP tier 1 action requested | named approver | per playbook SLA |

## Change Management
Changes to this file follow governed-evolution rules:
1. PR required with diff review by ≥2 L9 architects
2. Semantic version bump mandatory
3. All in-flight playbook runs continue under previous version
4. New runs adopt new version at next dispatch

## ACAP Seven-Section Reference
All L9 playbooks must carry an `acap_profile:` block satisfying WEF ACAP 2026:
1. Identity and scope
2. Operating context (systems, data classes, jurisdictions)
3. Authority and consequential events (permitted/conditional/prohibited)
4. Controls and enforcement (hooks, IAM, logging, escalation)
5. Evaluation evidence (test suites, thresholds)
6. Monitoring and change log
7. Sign-offs and re-authorization cadence
