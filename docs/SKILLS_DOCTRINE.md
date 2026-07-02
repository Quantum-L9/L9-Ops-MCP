---
l9_schema: 1
artifact_type: documentation
tags: ['doctrine']
retrieval: on_demand
status: active
---
# SKILLS DOCTRINE — L9 Library System
<!-- version: 3.4.1 | date: 2026-06-18 | author: Igor Beylin -->
<!-- Changes from v3.3.0: Added §8 Trust Ladder gate for skill execution,
     §9 Memory Admission pre-condition, §10 Build Law, updated §7 security checklist -->

## §1 What a Skill Is

A skill is a portable, on-demand behavioral capability that an agent loads to perform
a specific output-producing task. Skills are distinct from kernels:

| Dimension | Kernel | Skill |
|-----------|--------|-------|
| Function | Constrains behavior | Enables output production |
| Format | YAML (machine-parsed) | SKILL.md (agent-loaded) |
| Load trigger | Ring + trust_level | Explicit agent load or trigger match |
| Scope | Session-wide | Task-scoped |
| Governance | Enforces invariants | Operates within invariants |
| Location | docs/kernels/ | skills/ |
| Eval | convergence_footer | eval_status in frontmatter |

Skills operate WITHIN kernel constraints. A skill cannot override a kernel hard_ban.

---

## §2 Canonical SKILL.md Structure

```markdown
---
# Frontmatter (YAML — machine-parseable)
id: <output-type>-<domain>
version: <semver>
title: <one line, <= 80 chars>
category: <memory|coding|strategy|analysis|writing|kernels|playbooks>
ring: R<N>
domain: <domain_slug>
model_target: <model-slug>, <model-slug>
activation_phase: on_demand
status: <active|experimental|deprecated>
author: Igor Beylin
created: YYYY-MM-DD
modified: YYYY-MM-DD
l9_aligned_version: v3.4.1
retrieval_keys: [comma, separated, keywords]
changes_from_v3.3.0: <string | "NEW SKILL" | "UNCHANGED">
source_harvest: <source if harvested>
security_ring: <none|review_required|custom_only>
trust_required: <L0|L1|L2|L3|L4|L5>
memory_writes: <true|false>  # if true, memory_admission_kernel.v1 required
---

# SKILL: <title>

## Trigger Description
<When should an agent load this skill? What problem does it solve?
 Trigger Triad: WHAT it produces | WHEN to load it | WHY a fresh prompt fails here.
 2-3 sentences. No wall of text.>

## Pre-Conditions
<List kernel dependencies and pre-conditions. If memory_writes: true, declare
 memory_admission_kernel.v1 as required. If trust_required >= L3, declare it.>

## Protocol (numbered steps — the skill's operational procedure)

## Output Format

## Hard Constraints (MUST NOT form)

## Tool Bindings

## Inputs

| Field | Type | Required | Description |

## Expected Output

## Eval Status
- last_tested: YYYY-MM-DD
- fixture: evals/datasets/<fixture_file>
- pass_rate: <float | pending>
```

---

## §3 Naming Convention

Pattern: `<output-type>-<domain>`
- output-type: what the skill produces (generate, review, optimize, analyze, extract)
- domain: what it operates on (kernel, module-spec, playbook, code, memory)

Examples:
  optimize-kernel, generate-module-spec, review-code-l9, extract-memory-candidates
  analyze-pr-diff, generate-skill-md, optimize-playbook

Anti-patterns:
  kernel-optimizer (noun-form, not output-type first)
  code-review (too generic, no output-type prefix)
  the-great-code-review-skill (never)

---

## §4 Folder Structure

```
skills/
  kernels/
    optimize-kernel/
      SKILL.md
      examples/
        example_01_input.yaml
        example_01_output.yaml
    generate-skill-md/
      SKILL.md
  memory/
    cursor-memory-kernel/
      SKILL.md
  coding/
    generate-module-spec/
      SKILL.md
    review-code-l9/
      SKILL.md
  strategy/
    blue-sky-analysis/
      SKILL.md
  playbooks/
    optimize-playbook/
      SKILL.md
```

One directory per skill. SKILL.md is the only required file.
Examples are optional but strongly encouraged for skills with non-obvious output format.

---

## §5 Modularity Rules

- One skill, one output type. A skill that produces two different artifact types must be split.
- DRY: if two skills share a protocol block, extract to a shared doc and link.
- No skill embeds a kernel body. Skills reference kernel IDs; they do not copy kernel content.
- No skill embeds a playbook. Skills invoke playbook triggers; they do not copy playbook steps.
- Maximum SKILL.md length: 200 lines. If longer, split into skill + referenced sub-procedures.

---

## §6 Trigger Description Quality Rule (Trigger Triad)

Every Trigger Description MUST answer:
1. WHAT does this skill produce?
2. WHEN should an agent load it (not a generic keyword match — be specific)?
3. WHY does a fresh prompt or standard model output fail here?

Bad:  "Use this skill for code review tasks."
Good: "Produces a structured review-result.json conforming to the 8-dimension
      L9 CODE_REVIEW_CI schema. Load when reviewing a PR diff against an L9 codebase.
      Without it, the agent produces unstructured prose that cannot be parsed by
      the CI gate or appended to the review audit log."

---

## §7 Security Vetting Checklist (third-party skills)

Before loading any skill not authored by Igor Beylin:

- [ ] Read the full SKILL.md — not just the trigger description
- [ ] Check security_ring field (custom_only = do not load from external source)
- [ ] Audit Tool Bindings: does the skill request filesystem, shell, network, or credential access?
- [ ] Verify scripts/ directory if present: read every line before execution
- [ ] Check for prerequisite install steps — ClawHavoc attack vector (Feb 2026)
- [ ] Verify source repo: stars, last commit date, author identity
- [ ] Red flags: requests credentials, generic "install this first" steps, no eval_status
- [ ] If in doubt: throwaway account test first, then review output before use

---

## §8 Trust Ladder Gate for Skill Execution (v3.4.1 — ADR-014)

Skills declare trust_required in frontmatter.
The calling agent MUST hold the declared trust level or higher to load the skill.

  trust_required: L0 — any agent (read/draft operations)
  trust_required: L2 — bounded execution, file writes
  trust_required: L3 — autonomous multi-step execution
  trust_required: L4 — sub-agent delegation
  trust_required: L5 — sovereign (Igor grant required)

Agents at lower trust than trust_required MUST escalate before loading the skill.
Skill MUST NOT be loaded in L0/L1 context if trust_required >= L2.

---

## §9 Memory Admission Pre-Condition (v3.4.1 — ADR-009)

Any skill that writes to persistent/durable memory MUST declare:
  memory_writes: true
in its frontmatter, and MUST include memory_admission_kernel.v1 in its
Pre-Conditions block.

The skill's Protocol MUST route all memory writes through the admission gate.
Direct writes to persistent store, database, or graph are forbidden.
Substrate-native scratch (Cursor notepad, etc.) is not durable memory.

---

## §10 Build Law (v3.4.1 — IdentityOS harvest)

No placeholders. No fake implementations. No TODO scaffolds masquerading as code.

Skills that are not fully implemented MUST be marked status: experimental.
Experimental skills MUST declare what is not yet implemented in a KNOWN GAPS section.
Never emit a stub Protocol as a deliverable.

---

## §11 Eval Requirements

Every active skill MUST have:
- eval_status.last_tested populated (not "pending" in production)
- At least one fixture in evals/datasets/ matching the skill id
- pass_rate >= 0.80 before status: active is set

Experimental skills may have pass_rate: pending.
Skills with pass_rate < 0.80 must revert to status: experimental.

---

## §12 Lifecycle States

| Status | Meaning | Loadable |
|--------|---------|---------|
| active | Eval-evidenced, production | Yes |
| experimental | New or draft, not yet evidenced | Igor consent |
| deprecated | Superseded | No |
| archived | Removed | No |

Deprecated skills MUST declare superseded_by: <skill_id>.

---

## Preserved non-regressive material from l9_final_pack_v3.3.0(3).zip::l9_final_pack/docs/SKILLS_DOCTRINE.md

<!-- L9_META
l9_schema: 1
origin: l9-kernel
layer: [doctrine, agent-rules]
tags: [L9_DOCTRINE, skills-doctrine, SKILL.md, agent-capability]
owner: platform
status: active
canonical_path: docs/SKILLS_DOCTRINE.md
version: 3.3.0
/L9_META -->

# SKILLS DOCTRINE
## L9 Skill Library — Authoring, Structure, and Governance Contract

**Version**: 3.3.0 | **Effective**: 2026-06-17

---

## 1. WHAT IS A SKILL

A skill is a **portable, loadable agent capability** — a SKILL.md file that an agent
loads on demand to acquire a specific procedural capability for the duration of a task.

Skills vs Kernels:

| Dimension | Kernel | Skill |
|---|---|---|
| What it governs | HOW the agent behaves (laws, contracts, constraints) | WHAT the agent can do (procedure, tool bindings, steps) |
| Load model | Ring-based or moderouter-triggered | Explicit trigger match or `gh skill install` / `npx skills add` |
| Body | Three-tier behavioral rules | SKILL.md structured procedure |
| Lifecycle | Session-persistent | Task-scoped |
| Location | `docs/kernels/{ring}/` | `skills/{domain}/` |

**Never embed kernel-style behavioral laws in a skill. Never embed skill-style procedures in a kernel.**

---

## 2. SKILL FOLDER STRUCTURE

```
skills/
├── harness/
│   ├── optimize-kernel/
│   │   └── SKILL.md
│   └── validate-harness/
│       └── SKILL.md
├── coding/
│   ├── review-code-l9/
│   │   └── SKILL.md
│   └── scaffold-node/
│       └── SKILL.md
└── {domain}/
    └── {skill-id}/
        └── SKILL.md
```

**Rules**:
- One directory per skill — never a flat SKILL.md in the domain root
- Directory name = skill_id — must match `id` field in SKILL.md
- No other files required in skill directory (keep it portable)
- Additional files (examples, fixtures) allowed but not required

---

## 3. SKILL NAMING CONVENTION

```
{output-type}-{domain}

Examples:
  optimize-kernel      ← output-type: optimize, domain: kernel
  review-code-l9       ← output-type: review, domain: code-l9
  scaffold-node        ← output-type: scaffold, domain: node
  validate-harness     ← output-type: validate, domain: harness

Rules:
  - kebab-case
  - output-type first (what the skill produces)
  - domain second (what it operates on)
  - no version suffix in skill_id — version lives in metadata block
  - maximum 32 characters
```

---

## 4. SKILL.md ANATOMY (mandatory structure)

Every SKILL.md MUST contain these sections in this order:

```markdown
## [skill-id]
<!-- metadata block — required fields listed in §5 -->

## Description
One paragraph. What this skill does, when to use it, what it produces.
Satisfies the Trigger Triad: objective trigger, surface trigger, negative trigger.

## Inputs
List of required and optional inputs. Type, format, source.

## Steps
Numbered procedure. Each step: concrete action, not abstract description.
No "think about" steps — every step is executable.

## Outputs
What the skill produces. Format, structure, destination.

## Tool Bindings
What tools this skill uses (file_read, bash, code_exec, etc.)
Security surface declared here.

## Security Notes
What file/shell/network/credential access this skill requires.
Any elevated permissions flagged explicitly.

## Examples
At least one worked example showing input → steps → output.
```

---

## 5. MANDATORY METADATA FIELDS (every SKILL.md)

```yaml
id: {skill-id}                          # required — must match directory name
version: {semver}                       # required
author: {team or handle}               # required
domain: {domain}                       # required — matches parent directory
use_case: {one-line description}       # required
model_target: [claude-3-5, gpt-4o]    # required — which models tested on
inputs:                                # required
  - name: {input_name}
    type: {type}
    required: true|false
    description: {description}
expected_output: {description}         # required
eval_status: pending|pass|fail         # required
last_tested: "{YYYY-MM-DD}"           # required
tool_bindings: [{tool1}, {tool2}]      # required — even if empty list
security_surface:                      # required
  file_access: read|write|none
  shell_access: true|false
  network_access: true|false
  credential_access: true|false
```

---

## 6. TRIGGER TRIAD (mandatory on every Description section)

Every skill's Description MUST satisfy the Trigger Triad:

1. **Objective trigger** — what goal activates this skill
2. **Surface trigger** — what artifact/file type it operates on
3. **Negative trigger** — when NOT to use it

**BAD**: "This skill optimizes kernels."
**GOOD**: "Use this skill when you need to bring an existing kernel into compliance with
         KERNEL_DOCTRINE.md — specifically when it lacks the Tier 1/Tier 2 structure,
         has a documentation-style use_when, or is missing required L9_META fields.
         Do NOT use this skill to author a new kernel from scratch (use generate-skill-md instead)
         or to evaluate a kernel's behavioral correctness (use validate-harness)."

---

## 7. SECURITY VETTING CHECKLIST

Before loading a third-party or community skill:

```
□ Source verified — repo has sustained activity (commits in last 90 days)?
□ Author has consistent identity — no throwaway account red flags?
□ SKILL.md fully read — no shell commands executing on user-controlled input?
□ tool_bindings declared — matches what the steps actually do?
□ security_surface declared — shell_access: false if no shell needed?
□ No `scripts/` directory executing at install time?
□ No credential_access: true without explicit operator authorization?
□ No network_access: true to unexpected endpoints?
□ Skill directory contains only SKILL.md and examples — no compiled binaries?
□ Tested in isolated session before granting production use?
```

**If any box is unchecked → do not load. Request author to address.**

---

## 8. QUALITY GATES (before merging a new skill)

```
□ SKILL.md structure complete (all 8 sections present)
□ All mandatory metadata fields populated
□ Description satisfies Trigger Triad
□ At least one worked example present
□ tool_bindings accurate (not over-declared, not under-declared)
□ security_surface declared accurately
□ eval_status set to "pending" until eval confirms
□ Skill directory name matches id field
□ AGENTS.md skill registry updated
□ Promptfoo fixture created in evals/datasets/skills/
□ No kernel content embedded (procedures only, no behavioral laws)
```

---

## 9. SKILL LIFECYCLE

| State | Meaning |
|---|---|
| `draft` | Authored, not yet eval-confirmed |
| `active` | Eval-confirmed, in production use |
| `deprecated` | Superseded — grace period active (30 days min) |
| `archived` | Retired — moved to skills/archive/ |

---

## 10. ANTI-PATTERNS

| Anti-pattern | Fix |
|---|---|
| Skill embeds kernel laws ("MUST NOT use eval()") | Reference kernel by path — skills describe procedure, kernels enforce behavior |
| Monolithic SKILL.md with 20 steps and 5 tool bindings | Split into multiple focused skills |
| Steps that say "think about X" instead of doing X | Every step must be a concrete executable action |
| Security surface undeclared | Declare even if all fields are false/none |
| Skill directory contains `install.sh` or compiled binary | Reject — execution at install time is a supply chain attack vector |
| Community skill used without vetting | Run §7 checklist before loading |
| Skill version not bumped after update | Semver bump required on every change |

