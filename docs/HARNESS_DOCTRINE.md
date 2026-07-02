<!-- L9_META
l9_schema: 1
origin: l9-kernel
layer: [doctrine, agent-rules]
tags: [L9_DOCTRINE, harness, single-version, anti-sprawl, anti-rot]
owner: platform
status: active
canonical_path: docs/HARNESS_DOCTRINE.md
version: 3.3.0
/L9_META -->

# HARNESS DOCTRINE
## L9 Coding Harness — Single-Version Integration Contract

> **Prime Directive**: One version. One location. Every agent loads it. No copies. No forks. No rot.

---

## 1. WHAT THE HARNESS IS

Two kernel files that enforce the complete L9 Constellation protocol boundary:

| Kernel | Path | Weight | What it enforces |
|---|---|---|---|
| `l9_coding_kernel.v1` | `docs/kernels/R5/l9_coding_kernel.v1.md` | 2.0 | TransportPacket wire contract, routing laws, handler interface, security, CI gates |
| `l9_build_kernel.v1` | `docs/kernels/R5/l9_build_kernel.v1.md` | 1.5 | Artifact quality gates, no-stub policy, operator readiness |

**These files exist in exactly one location.** Every skill, playbook, agent, and tool
references them by canonical path. No copies. No forks. No vendor lock.

---

## 2. AGENT LOAD PROTOCOL

`moderouter_kernel.v1` auto-triggers harness kernels based on objective detection.
No manual loading required for agents with AGENTS.md correctly configured.

```
Detect: code_generation OR handler_authoring OR constellation_node
        OR write_python OR coding OR api_design OR node_build OR code_review
  → Load: docs/kernels/R5/l9_coding_kernel.v1.md

Detect: artifact_review OR pack_validation OR release_prep
        OR handoff_pack OR generated_code_review OR build_quality
  → Load: docs/kernels/R5/l9_build_kernel.v1.md
```

Both kernels may be active simultaneously (total weight: 3.5 of 18.0 budget).

---

## 3. ANTI-SPRAWL RULES (hard violations)

- **MUST NOT** copy harness kernel content into any other file
- **MUST NOT** embed harness rules inside CLAUDE.md, .cursorrules, or system prompts verbatim
- **MUST NOT** maintain a "local version" in any product repo
- **MUST NOT** declare code shipped if `make harness` has not exited 0
- **MUST NOT** reference harness content by copy — always reference by canonical path

### What TO do instead
- Add `load: docs/kernels/R5/l9_coding_kernel.v1.md` to your project's AGENTS.md
- Reference enforcement rules as: "see l9_coding_kernel.v1 LAW-T1"
- Wire the moderouter triggers in AGENTS.md — that is the entire integration

---

## 4. UPDATE PROTOCOL

When the harness changes (new SDK field, new routing law, new CI check):

1. Edit canonical file at `docs/kernels/R5/l9_coding_kernel.v1.md` or `l9_build_kernel.v1.md`
2. Bump `version:` in L9_META block
3. Update `last_tested:` to today's date
4. Run `bash scripts/library_health.sh` — confirms no copies exist elsewhere
5. Run `npx promptfoo eval` against `evals/promptfooconfig.yaml` — confirms skill behavior
6. Commit: `feat(harness): l9_coding_kernel v{N} — {change summary}`

No other files need to change. The update propagates automatically to all consumers on next load.

---

## 5. VERSIONING POLICY

| Field | Format | Rule |
|---|---|---|
| `version` in L9_META | semver (e.g. 3.3.0) | Bump on every change |
| File name | `{id}.v1.md` — frozen | v1 is channel, not version — never rename |
| Commit tag | `harness/{kernel}/v{N}` | Tag on every version bump |

Breaking changes that require a new channel → create `l9_coding_kernel.v2.md` and update
AGENTS.md to reference v2. Never silently replace content without bumping `version` field.

---

## 6. HEALTH CHECK CADENCE

| Trigger | Action |
|---|---|
| Model upgrade | Run `validate-harness` skill against both kernels |
| Monthly | Run `bash scripts/library_health.sh` |
| Post-merge of any kernel PR | Run `npx promptfoo eval` |
| Any "agent not following harness" complaint | Run `validate-harness` immediately |

---

## 7. SCOPE EXCLUSIONS

- LangSmith — out of scope by operator decision
- Infrastructure kernels (Dockerfile, Terraform, k8s) — `l9-template` owns those
- Domain-specific business logic kernels — each lives in `docs/kernels/R5/` per domain
- Non-Constellation codebases — harness kernels do not apply outside L9 Constellation scope
