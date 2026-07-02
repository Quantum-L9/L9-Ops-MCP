---
name: microservice-build
version: 0.1.0
status: active
author: Igor Beylin
last-tested: 2026-06-17
eval-status: untested

description: |
  Builds a complete L9-compliant microservice from scratch: manifest, contracts, implementation, tests, validation, and ship verdict.
  Use when: building a new microservice, spinning up a node in the L9 constellation, greenfield service creation.
  Do NOT use when: incremental changes to an existing service — use a single skill instead.
  Signals: build a microservice, new service, scaffold service, create node, L9 microservice build, greenfield service, new service node

steps:
  - id: STEP-00
    name: Microservice Context Lock
    role: INTAKE
    file: steps/step-00-intake.md
    input-types: [USER_INPUT]
    output-type: ServiceContextRecord
    skip-condition: null
  - id: STEP-01
    name: Build Manifest Generation
    role: PLANNING
    file: steps/step-01-manifest.md
    input-types: [ServiceContextRecord]
    output-type: BuildManifest
    skip-condition: null
  - id: STEP-05
    name: Consistency Validation
    role: VALIDATION
    file: steps/step-05-validation.md
    input-types: [TestDocArtifact, ImplementationArtifactV1, ContractArtifact, BuildManifest, ServiceContextRecord]
    output-type: ArtifactBundle
    skip-condition: null

kernel-requirements:
  - execution_plan_kernel.v1
  - agent_review_kernel.v1
  - sandbox_isolation_kernel.v1
  - eval_harness_kernel.v1
  - agent_observability_kernel.v1
skill-requirements: []
total-steps: 17
steps-authored: 3
steps-pending: 14
estimated-turns: 40-60
---

# Microservice Build Pipeline

## Purpose
End-to-end orchestration for building an L9-compliant microservice. 17 steps from intake to ship verdict. Steps 02-04 and 06-16 pending authoring — author using `templates/playbook/step.md.template`.

## Flow Diagram

```mermaid
flowchart TD
    S00[STEP-00: Intake] --> S01[STEP-01: Manifest]
    S01 --> S02[STEP-02: Contracts]
    S02 --> S03[STEP-03: Implementation]
    S03 --> S04[STEP-04: Tests+Docs]
    S04 --> S05[STEP-05: Validation]
    S05 --> S06[STEP-06: Assembly]
    S06 --> S07[STEP-07: Improvement Audit]
    S07 --> S08[STEP-08: Improvement Impl]
    S08 --> S09[STEP-09: Red Team]
    S09 --> S10[STEP-10: Hardening]
    S10 --> S11[STEP-11: Readiness]
    S11 --> S12[STEP-12: Gap Fill]
    S12 --> S13[STEP-13: Ship Verdict]
    S13 --> S14[STEP-14: Blue Sky]
    S14 --> S15[STEP-15: Roadmap]
    S15 --> S16[STEP-16: Leverage Strike]
```

## Completion Criteria
- [ ] ShipVerdictRecord.verdict == READY with empty blockers list
- [ ] All CRITICAL validation checks pass in STEP-05

## Escalation Conditions
- STEP-05 fails twice -> escalate to: Igor Beylin
- ShipVerdictRecord.verdict == BLOCKED after gap-fill -> escalate to: Igor Beylin
