---
name: review-code-l9
description: |
  Performs an 8-dimension L9-compliant code review on a diff, file, or PR.
  Use when: reviewing a PR, auditing new code, validating an implementation against spec, checking a diff before merge.
  Do NOT use when: non-code review tasks (use a different skill).
  Signals: review code, review PR, code review, diff review, check implementation, audit code, validate against spec, L9 review

license: MIT
compatibility: |
  Tested: Claude Code, Claude Sonnet 4+
  Kernel alignment:
  - agent_review_kernel.v1
  - sandbox_isolation_kernel.v1

metadata:
  author: Igor Beylin
  version: 1.0.0
  last-tested: 2026-06-17
  model-target: claude-sonnet-4
  eval-status: untested
  tags: [code-review, quality, L9, governance]
---

# review-code-l9

## Overview
8-dimension review covering: correctness, security, observability, test coverage, L9 doctrine compliance, performance, maintainability, and blast radius. Produces a structured findings table and a VERDICT: APPROVE / REQUEST_CHANGES / BLOCK.

## When to Use
Signals: diff present, PR link provided, user says "review", "check this code", "validate implementation".

## Workflow

1. Load `agent_review_kernel.v1` Tier 1 and `sandbox_isolation_kernel.v1` Tier 1
2. Parse the diff/code into logical units
3. Run 8-dimension review grid
4. Classify each finding: BLOCK / REQUEST_CHANGES / SUGGEST / NOTE
5. Emit findings table + verdict + top-3 required actions

## Output Format

```markdown
## L9 Code Review: <subject>

| Dimension | Status | Findings |
|-----------|--------|----------|
| Correctness | PASS / FAIL | ... |
| Security | ... | ... |
| Observability | ... | ... |
| Test Coverage | ... | ... |
| L9 Doctrine | ... | ... |
| Performance | ... | ... |
| Maintainability | ... | ... |
| Blast Radius | ... | ... |

**VERDICT: APPROVE / REQUEST_CHANGES / BLOCK**

### Required Actions (if REQUEST_CHANGES or BLOCK)
1. ...
```
