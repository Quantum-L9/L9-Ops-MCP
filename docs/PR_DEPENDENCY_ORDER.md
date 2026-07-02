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
