---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# Step 05 — Run CI

**Input**: Implemented node directory from Step 04
**Output**: CI pass report
**Skill**: None (uses review-code-l9 skill optionally)
**Kernels active**: l9_coding_kernel.v1

## Action

1. Run validation workflow from Layer 14:
   ```bash
   python -m pip install -e ".[dev]"
   python scripts/validate_contracts.py
   python scripts/generate_schema.py
   ruff check src tests scripts
   mypy src
   pytest -q
   ```
2. Run `make harness` — the single gate command.
3. If any check fails: record specific failure, fix, re-run.
4. Run `review-code-l9` skill against the diff if changes are complex.

## Validation

`make harness` exits 0. All CI checks from Layer 14 pass.
Zero forbidden patterns (PacketEnvelope, print(), eval(), direct peer calls).

## Failure Recovery

Each Layer 14 CI check has a corresponding fix in l9_coding_kernel.v1 Layer 14.
Fix the specific violation — do not add exceptions or bypass checks.

## Handoff

CI-passed node → Step 06 (register-gate)
