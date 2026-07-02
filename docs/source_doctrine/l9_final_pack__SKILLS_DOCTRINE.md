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
