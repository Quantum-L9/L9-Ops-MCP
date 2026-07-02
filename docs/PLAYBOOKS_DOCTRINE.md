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

---

## Preserved non-regressive material from l9-pack-v3.4.1(3).zip::l9-pack-v3.4.1/PLAYBOOKS_DOCTRINE.md

# PLAYBOOKS DOCTRINE — L9 Library System
<!-- version: 3.4.1 | date: 2026-06-18 | author: Igor Beylin -->
<!-- Changes from v3.3.0: §4 Handoff Packets as Views (ADR-019 harvest),
     §5 Trust Ladder gate for playbook execution, §6 Memory Admission pre-condition,
     §9 Build Law. Initial doctrine creation (no equivalent in v3.3.0). -->

## §1 What a Playbook Is

A playbook is a directory-based, multi-step orchestration procedure that sequences
kernels and skills to accomplish a complex, repeatable objective.

| Dimension | Skill | Playbook |
|-----------|-------|---------|
| Function | Produces one output artifact | Orchestrates a multi-step workflow |
| Scope | Task-scoped | Objective-scoped (multiple sessions) |
| Format | Single SKILL.md | PLAYBOOK.md + steps/ directory |
| Calls | Tools directly | Invokes skills + kernels |
| State | Stateless | Stateful (hand-off packets between steps) |
| Branching | No | Yes (conditional step routing) |

The Playbook-vs-Skill decision rule:
- If the procedure produces a single artifact type in one pass -> SKILL
- If the procedure involves two or more distinct output artifacts OR spans multiple
  agent sessions OR requires conditional branching -> PLAYBOOK

---

## §2 Canonical Playbook Directory Structure

```
playbooks/
  <playbook-slug>/
    PLAYBOOK.md           # Master doc: metadata, step index, hand-off schema
    steps/
      01_<step-name>.md   # One file per step
      02_<step-name>.md
      ...
    schemas/
      handoff_<step>.schema.json   # Hand-off packet schemas (one per step output)
    examples/
      example_01/         # Optional: end-to-end example run
    evals/
      fixtures/           # Eval fixtures for this playbook
```

Each step file is a self-contained procedure. Steps are numbered sequentially.
Step files MUST NOT be longer than 80 lines. If longer, extract sub-procedure to a skill.

---

## §3 PLAYBOOK.md Structure

```markdown
---
id: <verb>-<domain>
version: <semver>
title: <one line, <= 80 chars>
category: <development|review|analysis|deployment|maintenance>
ring: R<N>
trust_required: <L0-L5>
memory_writes: <true|false>
status: <active|experimental|deprecated>
author: Igor Beylin
created: YYYY-MM-DD
modified: YYYY-MM-DD
l9_aligned_version: v3.4.1
changes_from_v3.3.0: <string | "NEW PLAYBOOK" | "UNCHANGED">
---

# PLAYBOOK: <title>

## Objective
<One sentence: what business/engineering outcome does this playbook produce?>

## Trigger Triad
<WHAT it orchestrates | WHEN to run it | WHY a single skill or ad-hoc approach fails>

## Pre-Conditions
<Required trust_level, kernel loads, and memory_admission pre-condition if applicable>

## Step Index

| Step | File | Produces | Hand-off Object |
|------|------|---------|----------------|
| 01 | steps/01_name.md | artifact_type | schemas/handoff_01.schema.json |
...

## Hand-off Packet Contract
<Declare that all hand-off packets are views (read-only projections). See §4.>

## Completion Criteria
<What does success look like? What output proves the playbook succeeded?>

## Eval Status
- last_tested: YYYY-MM-DD
- fixture: evals/fixtures/
- pass_rate: <float | pending>
```

---

## §4 Handoff Packets as Views (v3.4.1 — ADR-019 harvest)

This is an architecture invariant: handoff_packets_are_views: true

Hand-off packets passed between playbook steps are READ-ONLY projections of
the canonical graph, not copies of mutable state.

Rules:
- Every hand-off packet MUST have a schema in playbook/schemas/
- Hand-off packets are generated by the hydrator (via context_budget_kernel)
  using the same RuntimePayload assembly contract as agent context
- Steps MUST NOT mutate a received hand-off packet. To pass modified state,
  generate a NEW hand-off packet from the updated graph.
- The "canonical truth" is always the graph, not the packet. If a packet and
  the graph disagree, the graph wins.

Hand-off packet schema template:
```json
{
  "$id": "playbook/<id>/schemas/handoff_<step>.schema.json",
  "type": "object",
  "required": ["playbook_id", "step_id", "produced_at", "readonly", "payload"],
  "properties": {
    "playbook_id": { "type": "string" },
    "step_id": { "type": "string" },
    "produced_at": { "type": "string", "format": "date-time" },
    "readonly": { "type": "boolean", "const": true },
    "trust_level_at_creation": { "enum": ["L0","L1","L2","L3","L4","L5"] },
    "payload": { "type": "object", "description": "Step-specific output data" }
  }
}
```

---

## §5 Trust Ladder Gate for Playbook Execution (v3.4.1 — ADR-014)

Playbooks declare trust_required in frontmatter.
The calling agent must hold the declared trust level or higher.

Most playbooks require L3 (Execute-Autonomous) because they span multiple steps
autonomously. Any playbook that involves:
  - spawning sub-agents -> L4 minimum
  - external data sharing -> L3 + explicit consent check
  - destructive actions (delete, overwrite, deploy to prod) -> L3 + escalation_hook

Playbook escalation_hook:
If a step produces a destructive action, the playbook MUST pause and emit an
escalation request before proceeding, regardless of trust_level.

---

## §6 Memory Admission Pre-Condition (v3.4.1 — ADR-009)

Any playbook that writes state to durable memory MUST declare:
  memory_writes: true
in PLAYBOOK.md frontmatter.

The specific step that triggers the memory write MUST declare
memory_admission_kernel.v1 as a required pre-condition in the step file.

The step file's protocol MUST route the write through the admission gate.
No playbook step may bypass memory_admission_kernel.v1.

---

## §7 Step File Structure

```markdown
# Step NN: <Step Name>
<!-- playbook: <playbook-id> | step: NN | version: X.Y.Z -->

## Objective
<One sentence: what does this step produce?>

## Input
<What does this step receive? Hand-off packet from prior step + any new context.>

## Kernels Required
<List kernel_ids to load for this step only. Progressive disclosure — minimum set.>

## Skills Required
<List skill ids to load for this step only.>

## Protocol
1. ...
2. ...

## Output
<What artifact does this step produce? Schema reference.>

## Hard Constraints
- MUST NOT <action>

## Hand-off Packet
- Schema: ../schemas/handoff_NN.schema.json
- Type: read-only view (see PLAYBOOKS_DOCTRINE §4)
```

---

## §8 Decomposing Monolithic Playbooks

If you have a single markdown file longer than 200 lines that encodes a workflow,
it is a monolithic playbook. Decompose it:

Step 1: Extract natural step boundaries (identify phase transitions in the text).
Step 2: Create steps/NN_<name>.md for each phase.
Step 3: Identify what is passed between phases — define hand-off packet schemas.
Step 4: Write PLAYBOOK.md with step index table.
Step 5: Delete the original monolith (it is now superseded_by this playbook directory).

Reference decomposition: the microservice-pipeline playbook (v3.3.0 briefing):
  Before: 60,000 char monolith, one PLAYBOOK.md
  After:  PLAYBOOK.md (index) + 17 step files + 6 hand-off schemas

---

## §9 Build Law (v3.4.1 — IdentityOS harvest)

No placeholders. No fake implementations. No TODO scaffolds masquerading as code.

Unimplemented steps MUST be documented as phase items in plans/, not as stub step files.
Experimental playbooks MUST declare all unimplemented steps in a KNOWN GAPS section.
Never emit a placeholder step file as a deliverable.

---

## §10 Naming Convention

Pattern: <verb>-<domain>
  verb: deploy, review, onboard, audit, migrate, optimize, generate, validate
  domain: microservice, pr-pipeline, kernel-pack, memory-system, agent-fleet

Examples: deploy-microservice, review-pr-l9, audit-kernel-pack, migrate-memory-graph

---

## §11 Lifecycle States

| Status | Meaning | Executable |
|--------|---------|-----------|
| active | Eval-evidenced, production | Yes |
| experimental | New or incomplete | Igor consent |
| deprecated | Superseded | No |
| archived | Removed | No |

Deprecated playbooks MUST declare superseded_by: <playbook-id>.

