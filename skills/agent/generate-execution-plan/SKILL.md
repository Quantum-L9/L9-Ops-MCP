---
name: generate-execution-plan
description: |
  Creates a versioned, machine-readable YAML execution plan for multi-phase tasks.
  Use when: task spans 3+ files, multiple sessions, requires staged delivery, or needs a recoverable plan artifact.
  Do NOT use when: simple single-turn tasks that complete in one response.
  Signals: execution plan, multi-phase task, project plan, phased delivery, create plan, plan this work, staged execution, PLAN.yaml

license: MIT
compatibility: |
  Tested: Claude Code, Claude Sonnet 4+
  Kernel alignment:
  - execution_plan_kernel.v1

metadata:
  author: Igor Beylin
  version: 1.0.0
  last-tested: 2026-06-17
  model-target: claude-sonnet-4
  eval-status: untested
  tags: [planning, execution, agent, multi-session]
---

# generate-execution-plan

## Overview
Produces a PLAN.yaml with phased steps, per-step success criteria, recovery paths, and a completion checklist. Each step declares its input artifacts and output artifacts to enable stateless recovery.

## Workflow

1. Load `execution_plan_kernel.v1` Tier 1
2. Decompose the task into phases (max 7 per plan, break into sub-plans if larger)
3. For each phase: define WHAT (output artifact), HOW (key decisions), DONE WHEN (acceptance criteria)
4. Identify recovery path for each phase (what to do if step fails)
5. Output: complete PLAN.yaml + human-readable summary table

## Output Format

```yaml
plan-id: <id>
version: 1.0.0
created: <date>
model: <model>
task: <one line>

phases:
  - id: PHASE-00
    name: <name>
    outputs: [<artifact>]
    done-when: <criterion>
    recovery: <recovery instruction>
```
