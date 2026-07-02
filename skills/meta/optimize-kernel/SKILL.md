---
id: optimize-kernel
version: 1.1.0
title: Kernel Optimizer — Apply Doctrine to Existing Kernels
category: kernels
ring: R5
domain: kernel_authoring
model_target: claude-sonnet, claude-opus
activation_phase: on_demand
status: active
author: Igor Beylin
created: 2026-06-17
modified: 2026-06-18
l9_aligned_version: v3.4.1
retrieval_keys: [optimize_kernel, kernel_optimizer, kernel_audit, doctrine_compliance, trigger_triad, tier_structure]
changes_from_v3.3.0: >
  v1.1.0: Added v3.4.1 compliance checks — trust_ladder_integration check,
  memory_admission_kernel requires check, hydrator_contract check, Build Law
  (no placeholders) enforcement, architecture_invariants compliance.
trust_required: L3
memory_writes: false
security_ring: none
---

# SKILL: optimize-kernel

## Trigger Description

Audits an existing kernel YAML against KERNEL_DOCTRINE.md and outputs an optimized
version with an audit report and diff summary. Load when onboarding a kernel authored
before v3.4.1 or when a kernel fails the authoring checklist. Without it, doctrine
upgrades (especially the v3.4.1 harvest additions) accumulate as undeclared technical debt.

## Pre-Conditions

- Load KERNEL_DOCTRINE.md before running
- Requires trust_level L3 (autonomous multi-step audit + rewrite)
- No memory writes; no admission gate required

## Protocol

1. Parse input kernel YAML against canonical structure (§4 of KERNEL_DOCTRINE.md)
2. Run KERNEL_DOCTRINE.md §14 Authoring Checklist — flag each failure
3. Check Trigger Triad in purpose: (WHAT / WHEN / WHY) — rewrite if only documentation
4. Check overload_weight declared and <= 18.0 session budget impact
5. Check all hard_bans use MUST NOT form, one per line
6. Check fail_closed intentionally set (not default-zero)
7. Check convergence_footer.unknowns documents open questions
8. [v3.4.1] Check trust_ladder_kernel.v1 in requires: if kernel gates R5 resources
9. [v3.4.1] Check memory_admission_kernel.v1 in requires: if kernel writes to memory
10. [v3.4.1] Check changes_from_v3.3.0 field populated
11. [v3.4.1] Check no placeholders, stubs, or TODO comments (Build Law)
12. [v3.4.1] Check architecture_invariants compliance (no hard ban contradicts any of 14 invariants)
13. Produce: audit_report.yaml + optimized kernel YAML + diff_summary.md
14. Bump minor version (e.g., 1.0.0 -> 1.1.0) on any structural change

## Output Format

```
kernel-audit/
  <kernel_id>_audit_report.yaml   # per-check pass/fail with rationale
  <kernel_id>_optimized.yaml      # doctrine-compliant kernel
  <kernel_id>_diff_summary.md     # human-readable what changed and why
```

## Hard Constraints

- MUST NOT alter kernel hard_bans without explicitly flagging the change in diff_summary
- MUST NOT remove existing unknowns from convergence_footer — only add new ones
- MUST NOT change kernel_id, ring, or category without explicit instruction
- MUST NOT output placeholder fields or stub behaviors in optimized kernel

## Tool Bindings

| Tool | Purpose | Required |
|------|---------|---------|
| KERNEL_DOCTRINE.md | Compliance reference | Yes |
| trust_ladder_kernel.v1 | Trust level (L3 required) | Yes |

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| kernel_yaml | string | yes | Full YAML content of kernel to optimize |
| doctrine_version | string | no | Default: v3.4.1 |

## Eval Status
- last_tested: 2026-06-18
- fixture: evals/datasets/optimize_kernel_fixtures.yaml
- pass_rate: pending
