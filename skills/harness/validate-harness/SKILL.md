<!-- L9_META
id: validate-harness
version: 1.0.0
author: platform
domain: harness
use_case: Validate that the L9 coding harness kernels behave correctly with the current model
model_target: [claude-sonnet-4, claude-3-5-sonnet]
inputs:
  - name: test_scope
    type: string enum
    required: false
    description: "all | coding | build — defaults to all"
  - name: model_tag
    type: string
    required: false
    description: Model identifier being tested (e.g. claude-sonnet-4-20261015)
expected_output: Validation report with per-law PASS/FAIL results and eval_status verdict
eval_status: pending
last_tested: "2026-06-17"
tool_bindings: [file_read, bash]
security_surface:
  file_access: read
  shell_access: true
  network_access: false
  credential_access: false
/L9_META -->

## validate-harness

## Description

Use this skill when you need to confirm that the L9 coding harness kernels
(`l9_coding_kernel.v1` and `l9_build_kernel.v1`) still produce correct behavior
with the current model — especially after a model upgrade, after a harness kernel
version bump, or in response to an "agent not following the harness" complaint.

**Objective trigger**: harness validation, model upgrade verification, eval run,
weekly health check, kernel regression test.
**Surface trigger**: any session involving `l9_coding_kernel.v1.md` or `l9_build_kernel.v1.md`.
**Negative trigger**: Do NOT use this skill to optimize kernel structure (use optimize-kernel).
Do NOT use this skill for general code review (use review-code-l9).

## Inputs

- `test_scope` (optional): `all` | `coding` | `build` — defaults to `all`
- `model_tag` (optional): model identifier for logging in the report

## Steps

1. **Read harness kernels**: Load `docs/kernels/R5/l9_coding_kernel.v1.md` and/or
   `docs/kernels/R5/l9_build_kernel.v1.md` depending on test_scope.
2. **Run Promptfoo eval**: Execute `npx promptfoo eval --config evals/promptfooconfig.yaml`
3. **Parse results**: Extract per-test PASS/FAIL from eval output.
4. **Check harness copy sprawl**: Run `bash scripts/library_health.sh` — confirms no
   duplicate copies exist outside the canonical paths.
5. **Check version consistency**: Confirm version field in L9_META matches the latest
   git tag for the harness.
6. **Check last_tested date**: If > 30 days old, flag as stale regardless of eval result.
7. **Generate validation report**: Per-law test results + copy-sprawl check + version check
   + stale date flag + overall verdict.
8. **Update eval_status**: If all pass → set `eval_status: pass` in both kernel files and
   update `last_tested`. If any fail → set `eval_status: fail` and list specific failures.

## Outputs

Validation report containing:
- Per-law eval results (PASS/FAIL with evidence)
- Copy sprawl check result
- Version consistency check
- Stale date flag (if applicable)
- Overall verdict: `harness_valid` | `harness_degraded` | `harness_failed`
- Recommended action if not `harness_valid`

## Tool Bindings

- `file_read`: load kernel files and config
- `bash`: run `npx promptfoo eval` and `bash scripts/library_health.sh`

## Security Notes

- Shell access required for Promptfoo eval and health check script
- No network access required (eval runs locally)
- No credential access required
- Read-only file access to kernel files (write only to update eval_status field)
