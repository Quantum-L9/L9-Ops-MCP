<!-- L9_META
l9_schema: 1
origin: l9-kernel
layer: [docs, runbook]
tags: [L9_KERNEL, runbook, operator-readiness]
owner: platform
status: active
canonical_path: RUNBOOK.md
version: 3.3.0
/L9_META -->

# RUNBOOK — L9 Library Operations

---

## Instant Setup

```bash
# Clone and navigate to repo root
cd your-repo

# Confirm library structure is intact
bash scripts/library_health.sh

# Confirm harness evals pass
npm install -g promptfoo   # if not installed
npx promptfoo eval --config evals/promptfooconfig.yaml
```

Expected: `library_health.sh` exits 0. Promptfoo reports all 9 tests PASS.

---

## Common Operations

### Optimize an existing kernel
```bash
# Load optimize-kernel skill in your agent session
# Feed the kernel file path
# Review audit report
# Commit the optimized file
git add docs/kernels/R5/{kernel}.md
git commit -m "feat(kernel): optimize {kernel} — KERNEL_DOCTRINE.md compliance"
```

### Add a new skill
```bash
mkdir -p skills/{domain}/{skill-id}
# Author skills/{domain}/{skill-id}/SKILL.md per SKILLS_DOCTRINE.md §4
# Update AGENTS.md skill registry
# Create eval fixture in evals/datasets/
# Run promptfoo eval to confirm behavior
```

### Add a new playbook
```bash
mkdir -p playbooks/{playbook-id}/steps
mkdir -p playbooks/{playbook-id}/handoffs/examples
# Author PLAYBOOK.md per PLAYBOOKS_DOCTRINE.md §3
# Author each step file per PLAYBOOKS_DOCTRINE.md §5
# Define typed handoff schemas per PLAYBOOKS_DOCTRINE.md §6
# Update AGENTS.md playbook registry
```

### Update the harness
```bash
# 1. Edit the canonical file
vi docs/kernels/R5/l9_coding_kernel.v1.md   # or l9_build_kernel.v1.md

# 2. Bump version in L9_META block, update last_tested date

# 3. Confirm no copies created
bash scripts/library_health.sh

# 4. Run evals
npx promptfoo eval --config evals/promptfooconfig.yaml

# 5. Commit with tag
git add docs/kernels/R5/l9_coding_kernel.v1.md
git commit -m "feat(harness): l9_coding_kernel v{N} — {change summary}"
git tag harness/l9_coding_kernel/v{N}
```

### Monthly health check
```bash
bash scripts/library_health.sh
bash scripts/audit_hardban_duplication.sh
npx promptfoo eval --config evals/promptfooconfig.yaml
```

### After model upgrade
```bash
# 1. Run validate-harness skill — checks both kernels against new model
# 2. Review per-law results
# 3. If any FAIL: update the offending rule in the canonical kernel file
# 4. Bump version, update last_tested, run evals again
# 5. Set eval_status: pass when all tests pass
```

---

## Required Environment

- Node.js (for `npx promptfoo eval`)
- bash >= 4.0
- An AI agent with access to `docs/kernels/R5/` files
- Git

---

## Expected Outputs

| Command | Expected output |
|---|---|
| `bash scripts/library_health.sh` | `STATUS: ✅ PASS — library is healthy` |
| `bash scripts/audit_hardban_duplication.sh` | `PASS: no universal hard ban duplication found` |
| `npx promptfoo eval` | 9/9 tests pass |

---

## Known Failure Modes

| Failure | Cause | Fix |
|---|---|---|
| `library_health.sh` FAIL: copies found | Harness file copied into product repo | Delete copy; reference by canonical path |
| `library_health.sh` WARN: stale dates | Kernels not re-tested after model upgrade | Run validate-harness skill; update last_tested |
| Promptfoo FAIL: LAW-T1 test | Model not loading coding kernel or ignoring it | Confirm AGENTS.md harness trigger wired |
| `eval_status: fail` in kernel | Recent model changed behavior | Run optimize-kernel + validate-harness cycle |

---

## Agent / Operator Handoff

To onboard a new agent or team member:
1. Point them at `AGENTS.md` — this is the entry point for all sessions
2. Confirm `moderouter_kernel.v1` is configured (auto-loads harness on coding objectives)
3. Run `bash scripts/library_health.sh` to confirm the library is in a clean state
4. For their first coding task: confirm `make harness` passes in their environment
