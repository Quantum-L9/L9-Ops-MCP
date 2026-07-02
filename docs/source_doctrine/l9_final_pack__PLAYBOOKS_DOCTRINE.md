<!-- L9_META
l9_schema: 1
origin: l9-kernel
layer: [doctrine, agent-rules]
tags: [L9_DOCTRINE, playbooks-doctrine, workflow, orchestration]
owner: platform
status: active
canonical_path: docs/PLAYBOOKS_DOCTRINE.md
version: 3.3.0
/L9_META -->

# PLAYBOOKS DOCTRINE
## L9 Playbook Library — Authoring, Structure, and Governance Contract

**Version**: 3.3.0 | **Effective**: 2026-06-17

---

## 1. WHAT IS A PLAYBOOK

A playbook is a **typed multi-step workflow for a specific, recurring use case** — a
PLAYBOOK.md directory that orchestrates skills, kernel contexts, and handoff objects
to produce a defined outcome.

Playbooks vs Skills vs Kernels:

| Dimension | Kernel | Skill | Playbook |
|---|---|---|---|
| Unit of work | Behavioral constraint | Single capability | Multi-step workflow |
| Structure | Tier 1/2/3 rules | SKILL.md procedure | PLAYBOOK.md + steps/ dir |
| Lifecycle | Session-persistent | Task-scoped | Single invocation |
| Orchestrates | Nothing (consumed) | Tools + context | Skills + kernels + handoffs |
| Reuse model | Loaded by reference | Loaded on trigger | Invoked by name |

**A playbook is a directory, not a file.** Any use case complex enough to require a flat
PLAYBOOK.md with inline steps is complex enough to deserve a `steps/` directory.

---

## 2. PLAYBOOK DIRECTORY STRUCTURE

```
playbooks/
└── {playbook-id}/
    ├── PLAYBOOK.md           # Metadata, overview, step manifest, handoff schema
    ├── steps/
    │   ├── 01-{step-name}.md
    │   ├── 02-{step-name}.md
    │   └── ...
    └── handoffs/
        ├── {handoff-type}.schema.yaml   # typed handoff object schemas
        └── examples/
            └── {example}.yaml
```

**Rules**:
- `PLAYBOOK.md` is the entry point — it references steps, never contains inline step logic
- Each step file: one executable action, one output, one handoff
- `handoffs/` contains typed schema files for inter-step objects — never raw dicts
- Playbook directory name = playbook_id

---

## 3. PLAYBOOK.md ANATOMY (mandatory structure)

```markdown
## [playbook-id]
<!-- metadata block — see §4 -->

## Overview
What this playbook accomplishes, when to invoke it, what it produces.
Trigger: what condition initiates this playbook.
Termination: what condition means the playbook is complete.

## Prerequisites
What must exist before step 01 executes.
Skills loaded, kernels active, environment ready.

## Step Manifest
| Step | File | Input | Output | Skill used |
|---|---|---|---|---|
| 01 | steps/01-{name}.md | {input type} | {output type} | {skill-id} |
...

## Handoff Schema
Reference to handoffs/ directory. Typed objects passed between steps.

## Known Failure Modes
What breaks and how to recover.

## Success Criteria
Observable conditions that confirm the playbook completed correctly.
```

---

## 4. MANDATORY METADATA FIELDS (every PLAYBOOK.md)

```yaml
id: {playbook-id}                       # required — must match directory name
version: {semver}                       # required
author: {team or handle}               # required
domain: {domain}                       # required
use_case: {one-line description}       # required
trigger: {what invokes this playbook}  # required
skills_required: [{skill-id}]          # required
kernels_required: [{kernel-id}]        # required
estimated_steps: {int}                 # required
handoff_schema_version: {semver}       # required
eval_status: pending|pass|fail         # required
last_tested: "{YYYY-MM-DD}"           # required
```

---

## 5. STEP FILE ANATOMY

Each file in `steps/` MUST be:

```markdown
# Step NN — {Step Name}

**Input**: {typed input — reference handoff schema}
**Output**: {typed output — reference handoff schema}
**Skill**: {skill-id} | None
**Kernels active**: {kernel-id list}

## Action
Numbered, concrete actions. No abstract descriptions.
Every action is executable by an agent with the listed skill and kernels active.

## Validation
How to confirm this step succeeded before proceeding to the next step.

## Failure Recovery
What to do if this step fails.

## Handoff
The typed object passed to the next step. Reference handoffs/{type}.schema.yaml.
```

**The monolith rule**: A step file that is longer than 80 lines is trying to be a playbook.
Split it.

---

## 6. TYPED HANDOFF OBJECTS

The **most important architectural decision** in a playbook is what gets passed between steps.

```yaml
# handoffs/node-spec.schema.yaml
---
$schema: "http://json-schema.org/draft-07/schema#"
title: NodeSpec
description: Typed handoff object passed from step 02 to step 03 in new-constellation-node
version: "1.0.0"
type: object
required: [node_id, actions, domain, priority_class]
properties:
  node_id:
    type: string
    pattern: "^[a-z0-9][a-z0-9-]{0,62}$"
  actions:
    type: array
    items: { type: string }
    minItems: 1
  domain:
    type: string
  priority_class:
    type: string
    enum: [P0, P1, P2, P3]
```

**Rules**:
- Every inter-step handoff MUST have a typed schema
- No raw dicts as handoff objects
- Schema version MUST be bumped if handoff structure changes
- Examples in `handoffs/examples/` — at least one per handoff type

---

## 7. PLAYBOOK vs SKILL DECISION TABLE

| Condition | Use |
|---|---|
| Single capability, single output, < 5 steps | Skill |
| Multiple capabilities chained, typed inter-step objects | Playbook |
| Requires coordination across multiple kernels | Playbook |
| Can be invoked identically from any context | Skill |
| Has prerequisites that must be validated before start | Playbook |
| Produces intermediate artifacts that inform later steps | Playbook |
| Under 15 minutes of execution time, stateless | Skill |
| Stateful across steps (step 3 depends on step 1 output) | Playbook |

---

## 8. REFERENCE IMPLEMENTATION — new-constellation-node

The `playbooks/new-constellation-node/` playbook is the reference implementation.
Before authoring a new playbook, read its structure.

**What it demonstrates**:
- PLAYBOOK.md as TOC with step manifest, not inline logic
- steps/ directory with 7 typed step files
- handoffs/ with typed NodeSpec, HandlerSpec, and RegistrationResult schemas
- Failure recovery at each step
- Success criteria per step and globally

---

## 9. QUALITY GATES (before merging a new playbook)

```
□ PLAYBOOK.md structure complete (all 7 sections)
□ All mandatory metadata fields populated
□ steps/ directory exists — no inline step logic in PLAYBOOK.md
□ Every step file has Input/Output/Skill/Action/Validation/Failure Recovery/Handoff
□ Typed handoff schema for every inter-step object
□ At least one handoff example per schema
□ No step file exceeds 80 lines (monolith rule)
□ eval_status set to "pending" until eval confirms
□ AGENTS.md playbook registry updated
□ No kernel behavioral laws embedded (reference kernels, don't copy them)
□ No skill procedure steps embedded inline (reference skills, don't copy them)
```

---

## 10. ANTI-PATTERNS

| Anti-pattern | Fix |
|---|---|
| Monolithic PLAYBOOK.md with all steps inline | Move every step to steps/ directory |
| Raw dict as inter-step handoff | Define typed schema in handoffs/ |
| Step file that is 200 lines and does 7 things | Split into 7 step files |
| Playbook embeds kernel rules inline | Reference kernel by path |
| Playbook embeds skill procedure inline | Reference skill by id |
| No failure recovery per step | Every step must specify recovery path |
| No success criteria | Unverifiable playbook is untrustworthy |
| Playbook stored as single flat file | Always a directory |
