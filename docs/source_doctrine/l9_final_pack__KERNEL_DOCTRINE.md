<!-- L9_META
l9_schema: 1
origin: l9-kernel
layer: [doctrine, agent-rules]
tags: [L9_DOCTRINE, kernel-doctrine, taxonomy, versioning, governance]
owner: platform
status: active
canonical_path: docs/KERNEL_DOCTRINE.md
version: 3.3.0
/L9_META -->

# KERNEL DOCTRINE
## L9 Kernel Library — Authoring, Governance, and Lifecycle Contract

**Version**: 3.3.0 | **Effective**: 2026-06-17

---

## 1. WHAT IS A KERNEL

A kernel is a **structured context injection unit** — a file that loads a named set of
constraints, laws, and behavioral rules into an agent's active context for a session or task.

Kernels are NOT:
- Documentation pages
- READMEs
- Wall-of-text system prompts
- Tutorials

Kernels ARE:
- Executable behavioral contracts
- Progressive disclosure units (Tier 1 → Tier 2 → Tier 3)
- Versioned, owned, evaluated, and pruned artifacts

---

## 2. TAXONOMY

| Type | What it is | Where it lives | Load model |
|---|---|---|---|
| **Kernel** | Behavioral contract injected into agent context | `docs/kernels/{ring}/` | Ring-based (see §4) |
| **Skill** | Portable agent capability loaded on demand | `skills/{domain}/` | Trigger-matched |
| **Playbook** | Typed multi-step workflow, single use case | `playbooks/{id}/` | Explicit invocation |
| **Prompt** | Single-task instruction, stateless | `prompts/{domain}/` | Direct load |

Kernels govern how the agent behaves. Skills govern what the agent can do. Playbooks govern how
a specific workflow executes. Prompts are the smallest unit — no state, no lifecycle.

---

## 3. THREE-TIER STRUCTURE (mandatory on every kernel)

```markdown
## TIER 1 — CAPABILITY DECLARATION   (always loaded)
  capability, use_when, do_not_use_when, hard_bans

## TIER 2 — OPERATIONAL RULES        (loaded when load_condition matches)
  Full rule body, laws, contracts, examples

## TIER 3 — DEEP REFERENCE            (lazy — loaded only when explicitly needed)
  Edge cases, historical context, extended examples, migration notes
```

**Why**: Tier 1 alone fits in a minimal context budget. Tier 2 loads for active tasks.
Tier 3 never pollutes working context unless specifically required.

---

## 4. RING SYSTEM

| Ring | Load model | What goes here |
|---|---|---|
| R0 | Preload unconditionally, every session | Sovereignty, identity, behavioral core |
| R1 | Preload unconditionally | Cognitive, memory, planning, uncertainty |
| R2 | Preload unconditionally | Formatting, I/O contracts, validation, next-prompt |
| R3 | Preload unconditionally | World model, mode routing, session rehydration, transport |
| R4 | Preload unconditionally | Execution state, convergence, HVEC, cost, human-in-loop |
| R5 | On-demand, moderouter triggers | Primary task + developer support kernels |
| R6 | Lazy or on-demand | Meta, doc gardening, execution planning |

**Overload budget**: Total session weight MUST NOT exceed 18.0 weight units.
Weight declared in `overload_weight` field of each kernel's L9_META block.

---

## 5. MANDATORY METADATA SCHEMA (every kernel)

```yaml
# --- L9_META ---
l9_schema: 1
origin: {repo-name}                          # required
layer: [{layer-type}]                        # required — agent-rules|kernel|doctrine|etc
tags: [{tag1}, {tag2}]                       # required — at least L9_KERNEL
owner: {team}                                # required
status: active                               # active|deprecated|archived|draft
canonical_path: {relative-path-from-root}   # required — single source of truth
version: {semver}                            # required — e.g. 3.3.0
last_tested: "{YYYY-MM-DD}"                 # required
eval_status: pending|pass|fail              # required
overload_weight: {float}                     # required — contribution to 18.0 session budget
ring: {R0..R6}                               # required
load_condition: "{trigger expression}"       # required for R5+
requires: [{kernel_id}]                      # optional — hard dependencies
amplifies: [{kernel_id}]                     # optional — soft synergies
single_source_rule: "{prohibition statement}" # required
# --- /L9_META ---
```

---

## 6. TRIGGER TRIAD (mandatory on every use_when / load_condition)

Every kernel's `use_when` and `load_condition` MUST satisfy the Trigger Triad:

1. **Objective trigger** — what goal/task activates this kernel
2. **Surface trigger** — what artifact type or file pattern activates it
3. **Negative trigger** — explicit do_not_use_when condition

Without all three, the moderouter cannot make a reliable load decision.

**BAD**: `use_when: "code tasks"`
**GOOD**: `use_when: "code_generation OR handler_authoring OR constellation_node OR write_python"`
          `do_not_use_when: "non-L9 codebases, docs-only sessions, planning-only sessions"`

---

## 7. NAMING CONVENTION

```
{domain}_{function}_kernel.v{channel}.{ext}

Examples:
  l9_coding_kernel.v1.md
  eval_harness_kernel.v1.yaml
  sandbox_isolation_kernel.v1.yaml

Rules:
  - snake_case
  - version suffix is a CHANNEL identifier (v1, v2), not content version
  - content version lives in L9_META.version field (semver)
  - never rename a file — create a new channel if breaking changes required
  - .md for human-authored rich content, .yaml for machine-structured kernels
```

---

## 8. AUTHORING CHECKLIST

Before committing a new or updated kernel:

```
□ L9_META block present with ALL required fields
□ Tier 1 / Tier 2 structure present (Tier 3 optional)
□ load_condition satisfies Trigger Triad
□ overload_weight set — does total session weight stay under 18.0?
□ hard_bans are kernel-specific (universal bans not duplicated — ref UNIVERSAL_HARDBANS.md)
□ use_when is objective trigger, NOT documentation description
□ single_source_rule explicitly prohibits copying
□ version bumped from previous value
□ last_tested updated to today
□ eval_status set to "pending" until eval run confirms
□ AGENTS.md kernel registry updated with new entry
□ Promptfoo eval fixture created in evals/datasets/
```

---

## 9. LIFECYCLE STATES

| State | Meaning | Actions allowed |
|---|---|---|
| `draft` | Authored but not eval-confirmed | Load in dev sessions only |
| `active` | Eval confirmed, in production use | Load in all sessions |
| `deprecated` | Superseded by newer kernel, grace period active | Load with warning |
| `archived` | Retired — no longer loaded | Reference only, never load |

**Deprecation process**:
1. Set status to `deprecated` in L9_META
2. Add `superseded_by: {new_kernel_id}` to L9_META
3. Keep file for 30 days minimum
4. After 30 days: move to `docs/kernels/archive/`
5. Update AGENTS.md to point to replacement

---

## 10. ANTI-PATTERNS (kill on sight)

| Anti-pattern | Why it's deadly | Fix |
|---|---|---|
| **Wall-of-text kernel** | Blows context budget, no selective load possible | Apply three-tier structure |
| **Documentation-style use_when** | Moderouter loads wrong kernel or misses entirely | Use Trigger Triad |
| **Universal ban duplication** | Diverges from UNIVERSAL_HARDBANS.md, creates contradictions | Reference, don't copy |
| **Kernel copy in product repo** | Forks — drift guaranteed within 2 weeks | Single canonical path |
| **Missing eval_status** | No way to know if kernel actually works with current model | Run evals, set status |
| **Unbounded ring R5+ preload** | Blows 18.0 weight budget before actual task starts | Move to R5 on-demand |
| **Content version in filename** | l9_coding_kernel.v3.3.0.md breaks all existing references | Semver in L9_META only |
| **Implicit trigger** | Agent guesses wrong, loads kernel for wrong session | Explicit load_condition |

---

## 11. OPTIMIZE-KERNEL SKILL

Run `optimize-kernel` skill (ref: `skills/harness/optimize-kernel/SKILL.md`) against any
existing kernel that:
- Lacks the Tier 1 / Tier 2 structure
- Has a documentation-style use_when (no Trigger Triad)
- Is missing required L9_META fields
- Contains universal hard bans duplicated from UNIVERSAL_HARDBANS.md
- Has `eval_status: fail` or has never been tested against current model

The skill outputs: audit report → diff → optimized YAML/MD ready to drop in.
