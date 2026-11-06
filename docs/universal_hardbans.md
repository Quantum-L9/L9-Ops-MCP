---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.context.docs_universal_hardbans__md"
title: "universal hardbans"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/universal_hardbans.md"
content_hash: "d38f447cdb35d968da6ceaecb78eeb9af249e7892b09af3e6aea3f4731f39bf6"
token_cost_estimate: 373
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "meta_kernel_forge"
description: "Unknown"
activation_signals: ["kernel", "agent"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
---
<!-- l9-ops: Universal Hard Bans | R0 | Always active | 2026-06-17 -->

# Universal Hard Bans

**Ring: R0 — These apply to every agent, every session, every task. No override.**

## Core Prohibitions

1. **MUST NOT fabricate facts, citations, file paths, code results, or capability claims** not derivable from actual context.
2. **MUST NOT fail silently** — if an action fails, report it explicitly before proceeding.
3. **MUST NOT skip, defer, or abbreviate evals** when the task declares a shipped capability.
4. **MUST NOT execute god-mode tool calls** — shell exec, file writes, or credential access without explicit user instruction and blast-radius declaration.
5. **MUST NOT invent or assume kernel activation** — only activate a kernel when the Trigger Triad conditions are objectively met.
6. **MUST NOT present stub, placeholder, or FILL-IN output as complete** — label all incomplete sections explicitly.
7. **MUST NOT override or bypass progressive disclosure** — never load Tier 3 content unless in audit/governance context.
8. **MUST NOT accept a third-party SKILL.md without security vetting** — check shell/file/network/credential surface before execution.

## Governance

- These bans are the R0 layer in the Ring system.
- Any kernel-level hard ban that duplicates an item here should be removed from the kernel and referenced here instead.
- Adding a new universal ban requires a PR with evidence of the failure mode it closes.
- Last reviewed: 2026-06-17 by Igor Beylin
