---
id: "L9-Ops-MCP.context.docs_pr_dependency_order__md"
title: "PR DEPENDENCY ORDER"
artifact_type: "context"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/PR_DEPENDENCY_ORDER.md"
content_hash: "430349f64aac5adbd20a727f78f32074fbebb477d3bd898d7e040455555ac634"
token_cost_estimate: 209
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
# PR Dependency Order

## Current Lineage

- PR #1: graph export/import/sync adapter layer. Keep separate unless it is rebased into the consolidation branch.
- PR #2: Graphiti-backed hydrator and admission gate. Superseded by PR #3 only after PR #3 carries all required functionality.
- PR #3: active Graphiti/MCP consolidation and repair branch.

## Supersession Rule

A PR may be closed as superseded only when the replacement PR includes:

1. all unique files or a written exclusion rationale;
2. import/runtime checks for replacement entrypoints;
3. updated README/Makefile/CI proof gates;
4. explicit body note naming the superseded PR;
5. validation evidence or blocked validation reason.

## Recommended Action

Use PR #3 or a new branch from main as the consolidation PR. Close PR #2 after the replacement branch proves parity.
