---
name: optimize-kernel
description: |
  Transforms any l9-ops kernel YAML into a doctrine-compliant three-tier progressive disclosure structure.
  Use when: auditing an existing kernel, running the optimize-kernel CI step, or onboarding a kernel from another source.
  Do NOT use when: authoring a brand-new kernel from scratch (use templates/kernel.yaml.template instead).
  Signals: optimize kernel, audit kernel compliance, apply doctrine, kernel drift, tier structure missing, trigger triad missing, rewrite kernel

license: MIT
compatibility: |
  Tested: Claude Code, Claude Sonnet 4+
  Kernel alignment:
  - context_budget_kernel.v1
  - eval_harness_kernel.v1

metadata:
  author: Igor Beylin
  version: 1.0.0
  last-tested: 2026-06-17
  model-target: claude-sonnet-4
  eval-status: untested
  tags: [kernel, governance, doctrine, optimization]
---

# optimize-kernel

## Overview
Applies KERNEL_DOCTRINE.md to any kernel YAML: adds tier markers, rewrites the description as a Trigger Triad, ensures convergence_footer has lastRunDate/modelVersion, removes universal hard ban duplication, and produces a diff summary + audit report.

## When to Use
- An existing kernel lacks tier2_load / tier3_load markers
- The description field is documentation-style ("This kernel introduces...") rather than dispatch-style
- Adding a kernel from an external source or legacy format
- Running `make ci` and disclosure enforcement fails

## Workflow

1. Load this skill + load `context_budget_kernel.v1` Tier 1
2. Read the target kernel YAML in full
3. Audit against KERNEL_DOCTRINE.md checklist (§2.1–2.5, §3, §5)
4. Produce: (a) audit findings table, (b) optimized kernel YAML, (c) diff summary
5. Write optimized YAML to `kernels/optimized/` (overwrite source)
6. Run `make validate-wiring id=<kernelid>` and report result

## Output Format

```
### Audit Report: <kernel-id>
| Dimension | Finding | Action |
|-----------|---------|--------|
| Tier markers | Missing tier2_load | Added |
...

### Diff Summary
- Added: tier2_load, tier3_load markers
- Rewrote: description → Trigger Triad
- Added: lastRunDate, modelVersion to convergence_footer
- Removed: 2 hard bans already in universal_hardbans.md
```

## Examples

**Input:** `kernels/optimized/context_budget_kernel.v1.yaml` — description is documentation-style

**Output:** Audit report + optimized YAML with Trigger Triad description + tier markers added
