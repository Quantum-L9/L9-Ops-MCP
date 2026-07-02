---
l9_schema: 1
artifact_type: documentation
tags: ['doctrine', 'kernel']
retrieval: on_demand
status: active
---
# KERNEL DOCTRINE — L9 Agent System
<!-- version: 3.4.1 | date: 2026-06-18 | author: Igor Beylin -->
<!-- Changes from v3.3.0: §9 Trust Ladder, §10 Memory Admission, §11 Hydrator, §12 Build Law, §3 14 invariants -->

## §1 What a Kernel Is

A kernel is a load-bearing behavioral constraint for an L9 agent session.
It is NOT documentation. It is NOT a prompt template. It is a machine-readable
instruction that changes what the agent is allowed to do, must do, and must never do.

Every kernel has exactly one job. If a kernel has two jobs, split it.

---

## §2 The Ring System (R0-R6)

| Ring | Label | Load Strategy | Trust Required | Count v3.4.1 |
|------|-------|---------------|----------------|--------------|
| R0 | Immutable identity | Always | L0 | 2 |
| R1 | Always-on cognition | Always | L0 | 5 |
| R2 | IO + formatting | Always | L1 | 4 |
| R3 | Routing + rehydration | Always | L1 | 5 |
| R4 | Execution control | Always | L2 | 5 |
| R5 | Domain + governance | On demand | L3 | 21 |
| R6 | Meta / gardening | Lazy | L2 | 2 |

Trust gate: trust_ladder_kernel.v1 evaluates L0-L5 before R5 kernels load.

---

## §3 Architecture Invariants (14 — Machine-Readable)

```yaml
architecture_invariants:
  graph_is_canonical: true
  continuity_is_externalized: true
  runtime_context_is_ephemeral: true
  durable_memory_single_path: true
  substrate_native_memory_is_scratch_only: true
  handoff_packets_are_views: true
  adapters_are_dumb_translators: true
  hydration_precedes_generation: true
  policy_precedes_execution: true
  consent_precedes_external_sharing: true
  evals_are_mandatory: true
  provenance_is_preserved: true
  trust_is_explicit_not_implicit: true
  no_placeholders: true
```

These are kernel laws, not documentation. Any artifact violating an invariant is invalid.

---

## §4 Canonical YAML Structure

```yaml
# L9_META
# l9_schema: 1 | origin: l9-kernel | layer: kernel | ring: RN | category: X
# retrieval_keys: [...] | changes_from_v3.3.0: X
# /L9_META

kernel_id: <name>.v<N>
version: <semver>
ring: R<N>
category: <core|primary_task|developer_support|governance|meta>
title: <one line, <= 80 chars>
purpose: >
  <Trigger Triad: WHAT | WHEN | WHY — 3 sentences max>
activation_phase: <always|on_demand|lazy>
status: <active|deprecated|experimental>

meta_context:
  author: Igor Beylin
  created: YYYY-MM-DD
  modified: YYYY-MM-DD
  description: <gap closed + changes from prior version>
  l9_aligned_version: v3.4.1
  changes_from_v3.3.0: <string | "NEW KERNEL" | "UNCHANGED">

tags: [...]
requires: [...]

init:
  behavior: >
    <Imperative instructions only. No prose. Every sentence is a directive.>

overload_weight: <float>

session_hooks:
  - hook: <name>
    trigger: <on_load|on_every_turn|on_artifact_emit|on_session_end>
    description: <one sentence, imperative>

hard_bans:
  - MUST NOT <action>

fail_closed: <true|false>

compatibility:
  requires: [...]
  amplifies:
    - kernel_id: <id>
      multiplier: <float>
  max_overlap_percent: <int>

routing_hints:
  relevance_keywords: [...]
  artifact_types: [...]
  objective_classes: [...]

leverage_score: <float 1-10>

convergence_footer:
  status: <unknown|pass|fail>
  threshold: 0.05
  pass_count: <int>
  final_ratio: <float>
  artifact_type: yaml_kernel
  naming_compliance: snake_case_verified
  unknowns:
    - "U-NN: description"
```

---

## §5 Trigger Triad Rule (Purpose Field)

Every purpose: MUST answer three questions in <= 3 sentences:
1. WHAT does this kernel do?
2. WHEN does it fire?
3. WHY does it matter — what fails without it?

Bad:  "Governs model usage." (documentation)
Good: "Gates all model-tier routing decisions to enforce cost and quality constraints.
      Fires on every turn where a model call is about to be made. Without it, agents
      default to FRONTIER on every call, burning session budget in 4 minutes."

---

## §6 Three-Tier Progressive Disclosure

R5 kernels use three tiers to prevent overload_weight spikes:
- TIER-1 (always present): init.behavior + hard_bans
- TIER-2 (on demand): worked examples, edge cases
- TIER-3 (reference only): schema definitions, full spec — link, do not embed

---

## §7 Hard Ban Rules

- All hard bans use MUST NOT prefix. No variations.
- One ban per line. No compound bans.
- Bans describe forbidden behaviors, not goals.
- fail_closed: true — kernel blocks rather than degrades on violation.
  Required for: security, trust, and memory kernels. Default false for dev-support.

---

## §8 Overload Weight System

- Each kernel declares overload_weight (float, typically 0.5-1.5)
- Total loaded weight MUST NOT exceed 18.0 per session
- R0-R4 baseline: ~7.5 weight units
- R5 remaining budget: ~10.5
- context_budget_kernel enforces the 18.0 hard limit

Guidance by category:
  governance kernels (trust_ladder, memory_admission): 0.8-1.0
  domain kernels (developer_core, code_review_ci): 1.0-1.2
  utility kernels (formatting, validation): 0.5-0.8
  meta kernels (doc_gardener, execution_plan): 0.5

---

## §9 Trust Ladder Integration (v3.4.1 — ADR-014 harvest)

Trust level is NEVER assumed. It is earned and explicitly granted.

  L0 Observe: read-only, no tool calls with side effects
  L1 Assist: propose only, human approves execution
  L2 Execute-Bounded: execute within pre-approved scoped plan
  L3 Execute-Autonomous: multi-step autonomous within declared scope
  L4 Delegate: spawn sub-agents, delegate bounded tasks
  L5 Sovereign: full autonomous within kernel hard bans (Igor grant required)

Ring-to-trust mapping:
  R0-R1: L0 minimum | R2-R3: L1 minimum | R4: L2 minimum
  R5: L3 minimum | R6: L2 minimum

Every R5 kernel load MUST be preceded by trust_ladder_kernel.v1 evaluation.
If trust_level < L3, R5 kernels are gated and escalation is required.

Kernel authoring rule: add trust_ladder_kernel.v1 to requires: if kernel gates
resources that demand L3+ autonomy.

---

## §10 Memory Admission Gate (v3.4.1 — ADR-009 harvest)

The most important new law in v3.4.1.

No agent may write to durable memory without passing through memory_admission_kernel.v1.
This enforces the durable_memory_single_path invariant.

Five admission criteria (all must pass):
  1. relevance: semantic_score >= 0.65
  2. trust: L2 or higher
  3. consent: no external sharing without explicit grant
  4. deduplication: check graph before write
  5. provenance: source_agent_id + session_id + timestamp

Fail -> quarantine to memory_quarantine/. Never discard. Never bypass.
Substrate-native scratch is NOT durable memory.

Kernel authoring rule: add memory_admission_kernel.v1 to requires: if kernel
triggers or enables writes to persistent memory.

---

## §11 Hydrator / RuntimePayload Contract (v3.4.1 — ADR-011/019 harvest)

The hydrator assembles a scoped RuntimePayload before every generation turn.
It is the ONLY authorized path from graph/memory to agent context.
hydration_precedes_generation is an architecture invariant.

RuntimePayload assembly order:
  1. Resolve trust_level (trust_ladder_kernel)
  2. Fetch allowed_scopes for this agent/profile
  3. Pull graph slice (memory_admission_kernel-filtered writes only)
  4. Apply budget tiers (context_budget_kernel TIER-1 through TIER-5)
  5. Compress if > 80% budget
  6. Seal as RuntimePayload (read-only — handoff_packets_are_views: true)
  7. Emit to agent context

handoff_packets_are_views is an architecture invariant.
RuntimePayload is a read-only projection. Agents MUST NOT mutate it.
Playbook hand-off objects follow the same rule — see PLAYBOOKS_DOCTRINE.md §4.

---

## §12 Build Law (v3.4.1 — IdentityOS AGENTS.md harvest)

No placeholders. No fake implementations. No TODO scaffolds masquerading as code.

This is a kernel law, adopted verbatim from IdentityOS AGENTS.md.
Applies to: kernels, skills, playbooks, schemas, scripts, plans — everything.

If a component is not implemented, represent it as:
  - A named unknown in convergence_footer.unknowns (U-NN: description)
  - A phase item in plans/ execution plan artifact
  - Status: experimental in the kernel YAML

Never emit a stub, placeholder, or fake implementation as a deliverable.

---

## §13 Lifecycle States

| Status | Meaning | Permitted in production |
|--------|---------|------------------------|
| active | Current, tested, in use | Yes |
| experimental | New, not yet eval-evidenced | Igor consent required |
| deprecated | Superseded, still parseable | No — load blocker |
| archived | Removed from rotation | No |

Deprecated kernels MUST declare superseded_by: <kernel_id>

---

## §14 Authoring Checklist

Before marking a kernel active:
- [ ] Trigger Triad in purpose (WHAT / WHEN / WHY)
- [ ] overload_weight declared and session total checked (<=18.0)
- [ ] All hard_bans use MUST NOT form, one per line
- [ ] fail_closed intentionally set
- [ ] convergence_footer.unknowns documents all open questions
- [ ] trust_ladder_kernel.v1 in requires if kernel gates R5 resources
- [ ] memory_admission_kernel.v1 in requires if kernel writes to memory
- [ ] changes_from_v3.3.0 populated (or "NEW KERNEL" or "UNCHANGED")
- [ ] No placeholders, stubs, or TODO comments (Build Law §12)
- [ ] SHA256 hash appended to convergence_footer
