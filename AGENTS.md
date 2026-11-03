---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.context.agents__md"
title: "AGENTS"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "AGENTS.md"
content_hash: "d3b1a3841bd94e440807cb3fa9643d0126e1297c259a31eed65383dc01cab08e"
token_cost_estimate: 970
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "meta_kernel_forge"
description: "Unknown"
activation_signals: ["meta", "kernel", "agent", "compliance"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
---
# AGENTS.md

L9 agent operating table of contents. Doctrine is first-class system material: kernels, skills, playbooks, governance, contracts, and prompts are loadable artifacts, not optional reading.

## Load order

```
R0-R4 kernels: preload when present
R5 kernels: load on objective match
R6/meta kernels: lazy or explicit
Governance/contracts: load when task touches policy, validation, compliance, or repo operation
```

## Operator Profile

- [docs/profiles/USER.md](docs/profiles/USER.md)

## Kernel registry

- [docs/kernels/R0/soul_kernel.v1.yaml](docs/kernels/R0/soul_kernel.v1.yaml)
- [docs/kernels/R5/context_budget_kernel.v1.yaml](docs/kernels/R5/context_budget_kernel.v1.yaml)
- [docs/kernels/R5/l9_build_kernel.v1.md](docs/kernels/R5/l9_build_kernel.v1.md)
- [docs/kernels/R5/l9_coding_kernel.v1.md](docs/kernels/R5/l9_coding_kernel.v1.md)
- [docs/kernels/R5/memory_admission_kernel.v1.yaml](docs/kernels/R5/memory_admission_kernel.v1.yaml)
- [docs/kernels/R5/model_governance_kernel.v1.yaml](docs/kernels/R5/model_governance_kernel.v1.yaml)
- [docs/kernels/R5/preferences_kernel.v1.yaml](docs/kernels/R5/preferences_kernel.v1.yaml)
- [docs/kernels/R5/trust_ladder_kernel.v1.yaml](docs/kernels/R5/trust_ladder_kernel.v1.yaml)

## Skill registry

- [skills/agent/generate-execution-plan/SKILL.md](skills/agent/generate-execution-plan/SKILL.md)
- [skills/agents-project-memory/SKILL.md](skills/agents-project-memory/SKILL.md)
- [skills/code/review-code-l9/SKILL.md](skills/code/review-code-l9/SKILL.md)
- [skills/coding/generate-module-spec/SKILL.md](skills/coding/generate-module-spec/SKILL.md)
- [skills/coding/review-code-l9/SKILL.md](skills/coding/review-code-l9/SKILL.md)
- [skills/coding/scaffold-node/SKILL.md](skills/coding/scaffold-node/SKILL.md)
- [skills/docs/generate-skill-md/SKILL.md](skills/docs/generate-skill-md/SKILL.md)
- [skills/governance-hooks/SKILL.md](skills/governance-hooks/SKILL.md)
- [skills/harness/optimize-kernel/SKILL.md](skills/harness/optimize-kernel/SKILL.md)
- [skills/harness/validate-harness/SKILL.md](skills/harness/validate-harness/SKILL.md)
- [skills/kernels/optimize-kernel/SKILL.md](skills/kernels/optimize-kernel/SKILL.md)
- [skills/memory/cursor-memory-kernel/SKILL.md](skills/memory/cursor-memory-kernel/SKILL.md)
- [skills/meta/optimize-kernel/SKILL.md](skills/meta/optimize-kernel/SKILL.md)
- [skills/ops-recycling-compliance/SKILL.md](skills/ops-recycling-compliance/SKILL.md)
- [skills/strategy/blue-sky-analysis/SKILL.md](skills/strategy/blue-sky-analysis/SKILL.md)

## Playbook registry

- [playbooks/document-extraction/playbook.yaml](playbooks/document-extraction/playbook.yaml)
- [playbooks/invoice-ar-processing/playbook.yaml](playbooks/invoice-ar-processing/playbook.yaml)
- [playbooks/microservice-build/PLAYBOOK.md](playbooks/microservice-build/PLAYBOOK.md)
- [playbooks/multi-agent-routing/playbook.yaml](playbooks/multi-agent-routing/playbook.yaml)
- [playbooks/new-constellation-node/PLAYBOOK.md](playbooks/new-constellation-node/PLAYBOOK.md)
- [playbooks/vendor-onboarding/playbook.yaml](playbooks/vendor-onboarding/playbook.yaml)

## Key doctrine docs

- [docs/KERNEL_DOCTRINE.md](docs/KERNEL_DOCTRINE.md)
- [docs/SKILLS_DOCTRINE.md](docs/SKILLS_DOCTRINE.md)
- [docs/PLAYBOOKS_DOCTRINE.md](docs/PLAYBOOKS_DOCTRINE.md)
- [docs/HARNESS_DOCTRINE.md](docs/HARNESS_DOCTRINE.md)
- [docs/contracts/L9_CONTRACT_SPECIFICATIONS.md](docs/contracts/L9_CONTRACT_SPECIFICATIONS.md)
- [docs/governance/L9_GOVERNANCE_STACK.md](docs/governance/L9_GOVERNANCE_STACK.md)
- [schemas/kernel.canonical.schema.json](schemas/kernel.canonical.schema.json)
- [docs/METADATA_HEADER_POLICY.md](docs/METADATA_HEADER_POLICY.md)

## Source gap policy

The registry lists files physically present in this consolidated repo. Missing upstream references are not linked. They are captured in REGRESSION_GUARD.md instead of being faked.
