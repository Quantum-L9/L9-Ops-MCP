<!-- L9_META
id: optimize-kernel
version: 1.0.0
author: platform
domain: harness
use_case: Bring an existing L9 kernel into compliance with KERNEL_DOCTRINE.md
model_target: [claude-sonnet-4, claude-3-5-sonnet]
inputs:
  - name: kernel_file
    type: file path or pasted content
    required: true
    description: The existing kernel YAML or MD to optimize
  - name: target_ring
    type: string
    required: false
    description: Ring assignment (R0–R6) — inferred if omitted
expected_output: Audit report + diff + optimized kernel file ready to commit
eval_status: pending
last_tested: "2026-06-17"
tool_bindings: [file_read, file_write]
security_surface:
  file_access: read-write
  shell_access: false
  network_access: false
  credential_access: false
/L9_META -->

## optimize-kernel

## Description

Use this skill when you need to bring an existing kernel into compliance with
`docs/KERNEL_DOCTRINE.md` — specifically when it lacks the three-tier Tier 1/Tier 2
structure, has a documentation-style use_when that fails the Trigger Triad, is missing
required L9_META fields, or duplicates universal hard bans from UNIVERSAL_HARDBANS.md.

**Objective trigger**: kernel optimization, kernel compliance, kernel authoring, kernel upgrade.
**Surface trigger**: any `.yaml` or `.md` file in `docs/kernels/` that is being reviewed or updated.
**Negative trigger**: Do NOT use this skill to author a new kernel from scratch (use
the authoring section of KERNEL_DOCTRINE.md directly). Do NOT use it to evaluate behavioral
correctness of a running kernel (use validate-harness skill).

## Inputs

- `kernel_file` (required): file path or pasted content of the existing kernel
- `target_ring` (optional): R0–R6 ring assignment — inferred from load_condition if absent

## Steps

1. **Read kernel**: Load the full kernel file content.
2. **Audit against KERNEL_DOCTRINE.md**: Check each required field in the mandatory metadata
   schema (§5 of KERNEL_DOCTRINE.md). Record PASS/FAIL per field.
3. **Check three-tier structure**: Confirm TIER 1 and TIER 2 sections exist. If missing,
   plan restructure: extract always-loaded content → Tier 1, move rule body → Tier 2.
4. **Check Trigger Triad**: Does use_when satisfy objective trigger + surface trigger +
   negative trigger? If not, draft corrected use_when and do_not_use_when.
5. **Check load_condition**: Matches use_when triggers? Is it an explicit boolean expression?
   If it is a prose description, rewrite as explicit trigger list.
6. **Check hard_bans**: Are any universal bans from UNIVERSAL_HARDBANS.md duplicated?
   If yes, replace with reference: "universal bans — ref docs/contracts/UNIVERSAL_HARDBANS.md".
7. **Check single_source_rule**: Present? If not, add: "NEVER copy this file. Reference by
   canonical path only."
8. **Check overload_weight**: Present? If not, estimate based on tier 2 body line count:
   - < 100 lines → 0.5; 100–200 → 1.0; 200–400 → 1.5; > 400 → 2.0+
9. **Draft optimized kernel**: Apply all corrections. Preserve all original behavioral content —
   restructure only, never remove rules.
10. **Output audit report**: Per-field PASS/FAIL table + list of changes made + diff summary.
11. **Write optimized file**: Save to same path (or declare path if creating new file).
    Bump version field by patch (e.g. 3.2.1 → 3.2.2). Set last_tested to today. Set
    eval_status to "pending".

## Outputs

1. Audit report table (PASS/FAIL per doctrine check)
2. Change summary (what was restructured, what was added, what was removed)
3. Optimized kernel file at canonical_path with version bumped

## Tool Bindings

- `file_read`: read existing kernel file
- `file_write`: write optimized kernel file

## Security Notes

- No shell access required
- No network access required
- Read-write file access to docs/kernels/ only
- Never writes outside docs/kernels/ or the declared canonical_path

## Examples

**Input**: `docs/kernels/R5/sandbox_isolation_kernel.v1.yaml` — missing Tier 1 section,
use_when is a single prose sentence, no single_source_rule.

**Output**:
```
Audit Report — sandbox_isolation_kernel.v1.yaml
================================================
l9_schema:          PASS
origin:             PASS
layer:              PASS
tags:               PASS
owner:              PASS
status:             PASS
canonical_path:     PASS
version:            PASS
last_tested:        FAIL — missing
eval_status:        FAIL — missing
overload_weight:    FAIL — missing
ring:               PASS
load_condition:     FAIL — prose description, not explicit trigger expression
single_source_rule: FAIL — missing
Tier 1 structure:   FAIL — missing
Tier 2 structure:   PASS

Changes made:
  + Added last_tested: "2026-06-17"
  + Added eval_status: pending
  + Added overload_weight: 1.0
  + Rewrote load_condition as explicit trigger expression
  + Added single_source_rule
  + Extracted Tier 1 header from existing use_when
  + Wrapped existing body in TIER 2 section

Version bumped: 1.0.0 → 1.0.1
```
