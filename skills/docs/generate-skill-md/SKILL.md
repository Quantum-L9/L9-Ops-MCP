---
name: generate-skill-md
description: |
  Scaffolds a production-ready SKILL.md from a natural language description of the skill's purpose.
  Use when: authoring a new skill from scratch, onboarding an external skill into the l9-ops standard, generating skill structure from a requirements brief.
  Do NOT use when: modifying an existing skill (edit directly). Do NOT use when the description is too vague to produce a Trigger Triad.
  Signals: create skill, new skill, scaffold SKILL.md, write SKILL.md, add skill to library, skill template

license: MIT
compatibility: |
  Tested: Claude Code, Claude Sonnet 4+
  Kernel alignment: none required (meta-skill)

metadata:
  author: Igor Beylin
  version: 1.0.0
  last-tested: 2026-06-17
  model-target: claude-sonnet-4
  eval-status: untested
  tags: [meta, scaffolding, skills, library-ops]
---

# generate-skill-md

## Overview
Given a natural language description of a skill's purpose, produces a complete SKILL.md file following SKILLS_DOCTRINE.md, including a Trigger Triad description, frontmatter, workflow, output format, and example. Then calls `make add-skill` to wire it into the library.

## Workflow

1. Extract or request: skill ID, name, intended output, kernel dependencies
2. Construct Trigger Triad: capability statement, Use when, Do NOT use when, Signals (5-15 phrases)
3. Author: Overview, When to Use, Workflow, Output Format, Examples sections
4. Output: complete SKILL.md file content
5. Instruct user: `make add-skill id=<id> name="<name>" kernels="<k1,k2>"`
   then `make validate-wiring id=<id>`

## Output Format

Complete SKILL.md file — ready to copy to `skills/<category>/<id>/SKILL.md`.
