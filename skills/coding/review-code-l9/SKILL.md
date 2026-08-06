---
name: review-code-l9
description: "Review L9 Constellation node code against l9_coding_kernel.v1 laws. Use when reviewing a diff, file, or node for L9 coding-kernel compliance."
---
<!-- L9_META
id: review-code-l9
version: 1.0.0
author: platform
domain: coding
use_case: Review L9 Constellation node code against l9_coding_kernel.v1 laws
model_target: [claude-sonnet-4, claude-3-5-sonnet]
inputs:
  - name: diff_or_file
    type: git diff or file content
    required: true
    description: Code to review — can be a git diff, a single file, or a directory path
  - name: review_focus
    type: string enum
    required: false
    description: "all | transport | routing | security | testing | ci — defaults to all"
expected_output: Structured review with per-law PASS/FAIL findings and PR checklist
eval_status: pending
last_tested: "2026-06-17"
tool_bindings: [file_read, bash]
security_surface:
  file_access: read
  shell_access: true
  network_access: false
  credential_access: false
/L9_META -->

## review-code-l9

## Description

Use this skill when performing a code review on any L9 Constellation node codebase —
to verify the code satisfies the laws in `docs/kernels/R5/l9_coding_kernel.v1.md`.

**Objective trigger**: code review, PR review, merge check, constellation node code,
handler authoring review, L9 engine code inspection.
**Surface trigger**: Python files in `engine/`, `src/`, or `tests/` of an L9 node repo.
**Negative trigger**: Do NOT use for non-L9 codebases. Do NOT use for
infrastructure-only files (Dockerfile, Terraform, CI YAML with no Python).

## Inputs

- `diff_or_file` (required): git diff, file path(s), or directory to review
- `review_focus` (optional): `all` | `transport` | `routing` | `security` | `testing` | `ci`

## Steps

1. **Load harness**: Confirm `docs/kernels/R5/l9_coding_kernel.v1.md` is active.
   If not active in this session, load it now.
2. **Parse input**: Read the diff or file content.
3. **PacketEnvelope scan**: Search for any `PacketEnvelope` import. If found → FAIL (LAW-T1).
4. **Transport path scan**: Search for any non-TransportPacket execute path.
   Raw dict posts, typed alternate envelopes → FAIL (LAW-T1).
5. **Routing scan**: Search for node-to-node calls (`requests.post(peer_url)`,
   `httpx.post(node_url)`, hardcoded peer URLs). If found → FAIL (LAW-R2).
6. **Mutation scan**: Search for in-place packet mutation (attribute assignment on a
   TransportPacket without derive() or with_hop()). If found → FAIL (LAW-T5).
7. **Handler signature check**: All handlers in `engine/handlers.py` must be
   `async def X(packet: TransportPacket) -> TransportPacket`. If not → FAIL (LAW-T2).
8. **print() scan**: Any `print(` in Python files → FAIL (Layer 14).
9. **Banned pattern scan**: `eval(`, `exec(`, `compile(`, `yaml.load(` without SafeLoader,
   `raise NotImplementedError` → FAIL (Layer 11).
10. **L9_META check**: Every new file has L9_META header → PASS/FAIL (Layer 12).
11. **Test coverage check**: New handler without test → flag as gap (Layer 13).
12. **PR checklist**: Output the Layer 14 PR checklist with PASS/FAIL per item.
13. **Summary**: Blocking issues (hard FAIL) vs advisory issues vs PASS items.

## Outputs

- Per-law scan results (PASS/FAIL with line references)
- PR checklist with status
- List of blocking issues (must fix before merge)
- List of advisory issues (should fix, not blocking)
- Merge recommendation: APPROVE | REQUEST_CHANGES | BLOCK

## Tool Bindings

- `file_read`: read diff, files, or directory contents
- `bash`: run `grep` scans for banned patterns

## Security Notes

- Shell access for grep scans only — no write access
- No credential access required
- No network access required
