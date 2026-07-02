---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# L9-Ops-MCP

> **Operator:** Igor Beylin (Boss)
> **Version:** 3.4.0 — IgorOS Harvest Integration
> **Updated:** 2026-06-18

---

## What This Is

The single integrated L9 agent kernel and skill pack. Every file is:
1. **Canonically formatted** — required frontmatter headers for retrieval, tagging, and ring identification
2. **Retrieval-indexed** — `retrieval_keys` field on every artifact enables semantic search
3. **Ring-classified** — R0–R6 load order enforced via AGENTS.md registry
4. **Source-traced** — `source_files` field maps every artifact back to its IgorOS origin

---

## Quick Start

```bash
# Validate all canonical headers
make validate

# Run library health check
make health

# Audit all custom skills
make skill-audit

# Run full eval suite
make eval

# Bundle for deployment
make zip
```

---

## Repo Structure

```
l9-igoros-pack/
├── AGENTS.md                          # Master kernel + skill registry TOC (v3.4.0)
├── MANIFEST.json                      # Pack manifest with file index and change log
├── Makefile                           # Automation: validate, health, eval, zip
│
├── docs/
│   ├── profiles/
│   │   └── USER.md                    # Igor Beylin operator profile (v5.0.0)
│   └── kernels/
│       ├── R0/
│       │   ├── soul_kernel.v1.yaml    # Agent identity + runtime laws (from SOUL.md)
│       │   ├── master_sovereignty_kernel.v1.yaml
│       │   ├── identity_kernel.v1.yaml
│       │   └── behavioral_kernel.v1.yaml
│       ├── R1/  (memory, planning, cognition, world_knowledge, uncertainty)
│       ├── R2/  (formatting, io_contract, validation, next_prompt)
│       ├── R3/  (worldmodel, moderouter, domain_spec, session_rehydration, transport_packet)
│       ├── R4/  (execution_state, convergence, high_velocity, cost_tracking, human_in_loop)
│       ├── R5/
│       │   ├── preferences_kernel.v1.yaml  # Igor collaboration preferences (from PREFERENCES v4.5)
│       │   └── [22 more developer/task kernels]
│       └── R6/  (doc_gardener, execution_plan)
│
├── skills/
│   ├── memory/
│   │   └── cursor-memory-kernel/
│   │       └── SKILL.md               # Cursor session memory protocol (from cursor_memory_kernel.yaml)
│   ├── strategy/
│   │   └── blue-sky-analysis/
│   │       └── SKILL.md               # Universal strategic expansion (from Blue-Sky-Universal.md)
│   ├── coding/
│   │   └── generate-module-spec/
│   │       └── SKILL.md               # L9 module spec generator (from SuperPrompt v2.5)
│   └── meta/
│       └── optimize-kernel/
│           └── SKILL.md               # Kernel optimization skill (from KERNEL_DOCTRINE.md)
│
├── scripts/
│   ├── validate_headers.py            # Canonical header enforcement
│   ├── library_health.py              # Stale/rot/missing field detection
│   ├── skill_endpoint_audit.py        # Custom skill audit (exits 1 on failure)
│   └── harvest_audit.py               # IgorOS source-to-pack delta checker
│
└── evals/
    ├── promptfooconfig.yaml            # Promptfoo eval suite (8 tests)
    └── datasets/                       # Prompt fixtures per skill
```

---

## IgorOS Harvest Map

| IgorOS Source | Pack Target | Status |
|---|---|---|
| SOUL.md | docs/kernels/R0/soul_kernel.v1.yaml | Realigned + headers added |
| USER.md | docs/profiles/USER.md | Canonical format, headers added |
| PREFERENCES_v4.5.yaml | docs/kernels/R5/preferences_kernel.v1.yaml | Deduplicated, promoted to kernel |
| Igor_Beylin_Preferences_v4.5.yaml | (merged into preferences_kernel.v1) | Duplicate removed |
| cursor_memory_kernel.yaml | skills/memory/cursor-memory-kernel/SKILL.md | Wrapped as SKILL.md |
| Blue-Sky-Universal.md | skills/strategy/blue-sky-analysis/SKILL.md | Wrapped as SKILL.md |
| L9-SuperPrompt-Canonical-v2.5.md | skills/coding/generate-module-spec/SKILL.md | 6-pass workflow extracted |
| L9_Constellation_CKL_v1.0.md | OUT OF SCOPE (superseded) | Not harvested |
| Domain Enrichment briefs | OUT OF SCOPE | Not harvested |

---

## Non-Negotiables

- All skills are **custom** — no third-party skills
- `make skill-audit` exits 1 on any missing required field
- `make validate` exits 1 on any missing canonical header
- `soul_kernel.v1` and `USER.md` load at every session start
- `infra/skill_endpoint_audit.py` cron enforces skill health daily (see USER.md)

---

## Preserved non-regressive material from l9_final_pack_v3.3.0(3).zip::l9_final_pack/README.md

<!-- L9_META
l9_schema: 1
origin: l9-kernel
layer: [docs]
tags: [L9_KERNEL, library, readme]
owner: platform
status: active
canonical_path: README.md
version: 3.3.0
/L9_META -->

# L9 Prompt / Skill / Playbook Library

**v3.3.0 | 44 kernels | 4 skills | 1 playbook | 4 doctrines**

Elite-grade, doctrine-governed AI library infrastructure for L9 Constellation development.

---

## What is this

This library is the context engineering layer for the L9 system. It provides:

1. **Kernels** — behavioral contracts injected into agent context per session objective
2. **Skills** — portable agent capabilities loaded on demand (SKILL.md standard)
3. **Playbooks** — typed multi-step workflows with explicit handoff schemas
4. **Doctrines** — the governing rules for authoring, versioning, and maintaining each layer

The harness (l9_coding_kernel + l9_build_kernel) enforces the TransportPacket wire contract
and artifact quality gates across all L9 Constellation development. One version. No forks.

---

## Folder Map

```
.
├── AGENTS.md                        # Agent TOC — kernel registry, skill registry, triggers
├── README.md                        # This file
├── RUNBOOK.md                       # Instant setup + common operations
├── docs/
│   ├── KERNEL_DOCTRINE.md           # Kernel authoring, taxonomy, lifecycle
│   ├── SKILLS_DOCTRINE.md           # Skill authoring, structure, security vetting
│   ├── PLAYBOOKS_DOCTRINE.md        # Playbook authoring, typed handoffs
│   ├── HARNESS_DOCTRINE.md          # Harness single-version integration contract
│   └── kernels/
│       └── R5/
│           ├── l9_coding_kernel.v1.md   # TransportPacket wire contract + all laws
│           └── l9_build_kernel.v1.md    # Artifact quality gates + no-stub policy
├── skills/
│   ├── harness/
│   │   ├── optimize-kernel/SKILL.md    # Bring kernels into KERNEL_DOCTRINE compliance
│   │   └── validate-harness/SKILL.md   # Validate harness against current model
│   └── coding/
│       ├── review-code-l9/SKILL.md     # L9 code review against harness laws
│       └── scaffold-node/SKILL.md      # Scaffold new Constellation node from spec
├── playbooks/
│   └── new-constellation-node/
│       ├── PLAYBOOK.md                 # Step manifest + handoff schema index
│       ├── steps/                      # 7 typed step files
│       └── handoffs/                   # Typed inter-step object schemas
├── evals/
│   ├── promptfooconfig.yaml            # 9-test Promptfoo eval suite
│   └── datasets/                       # Eval fixtures per skill
└── scripts/
    ├── library_health.sh               # 5-check health gate
    └── audit_hardban_duplication.sh    # Universal ban duplication detector
```

---

## Core Execution Path

For a new Constellation node:
1. AGENTS.md → moderouter auto-loads `l9_coding_kernel.v1` on coding objective
2. Invoke `new-constellation-node` playbook
3. Playbook uses `scaffold-node` skill (Step 03)
4. `make harness` gates against `l9_coding_kernel.v1` laws
5. Node registers at Gate; health check confirms

For a kernel optimization:
1. Load `optimize-kernel` skill
2. Feed existing kernel file
3. Receive audit report + optimized file ready to commit

---

## How to Validate

```bash
bash scripts/library_health.sh       # 5 health checks
bash scripts/audit_hardban_duplication.sh  # ban duplication scan
npx promptfoo eval                   # 9 skill behavioral tests
```

---

## How to Extend

- **New kernel**: Follow KERNEL_DOCTRINE.md §8 authoring checklist. Add to AGENTS.md registry.
- **New skill**: Follow SKILLS_DOCTRINE.md §4 anatomy. Add to AGENTS.md skill registry.
- **New playbook**: Follow PLAYBOOKS_DOCTRINE.md §3 anatomy. Add to AGENTS.md playbook registry.
- **Update harness**: Edit canonical file. Bump version. Run health + eval. Commit.
  See HARNESS_DOCTRINE.md §4 update protocol.

---

## Out of Scope

- LangSmith (operator decision)
- Infrastructure kernels (Dockerfile, Terraform, k8s) — `l9-template` owns those
- Non-Constellation codebases


---

## Preserved non-regressive material from l9-pack-v3.4.1(3).zip::l9-pack-v3.4.1/README.md

# L9 Kernel + Skills + Playbooks Pack — v3.4.1

**Release date:** 2026-06-18
**Author:** Igor Beylin
**Base:** v3.3.0 + IdentityOS 6-concept harvest (ADR-009, ADR-011, ADR-014, ADR-019)

---

## What Changed in v3.4.1

6 architectural concepts harvested from IdentityOS (2026-05-16) and integrated as
first-class kernel laws:

| Concept | Source | Integration Point |
|---------|--------|------------------|
| Trust Ladder (L0-L5) | ADR-014 | trust_ladder_kernel.v1 (NEW) |
| Memory Admission Gateway | ADR-009 | memory_admission_kernel.v1 (NEW) |
| Architecture Invariants (14) | AGENTS.md | AGENTS.md + KERNEL_DOCTRINE §3 |
| Hydrator / RuntimePayload | ADR-011/019 | context_budget_kernel.v1 v1.1.0 |
| Handoff Packets as Views | ADR-019 | context_budget_kernel + PLAYBOOKS_DOCTRINE §4 |
| Build Law (no placeholders) | AGENTS.md | AGENTS.md + KERNEL_DOCTRINE §12 |

---

## Governing Doctrines

| File | Purpose | Version |
|------|---------|---------|
| KERNEL_DOCTRINE.md | Kernel authoring law | v3.4.1 |
| SKILLS_DOCTRINE.md | Skill authoring law | v3.4.1 |
| PLAYBOOKS_DOCTRINE.md | Playbook authoring law | v3.4.1 (NEW) |
| AGENTS.md | TOC + build law + 14 invariants | v3.4.1 |

---

## New Kernels

- `docs/kernels/R5/trust_ladder_kernel.v1.yaml` — L0-L5 earned autonomy (ADR-014)
- `docs/kernels/R5/memory_admission_kernel.v1.yaml` — Durable memory gate (ADR-009)

## Upgraded Kernels

- `docs/kernels/R5/model_governance_kernel.v1.yaml` — 1.0.0 -> 1.1.0 (trust_ladder integration)
- `docs/kernels/R5/context_budget_kernel.v1.yaml` — 1.0.0 -> 1.1.0 (hydrator_contract)

## New Schemas (IdentityOS)

- `schemas/identityos/runtime_context.schema.json`
- `schemas/identityos/runtime_payload.schema.json`
- `schemas/identityos/agent.schema.json`
- `schemas/identityos/profile.schema.json`

---

## Immediate Action Sequence

| Priority | Action | Command / File |
|----------|--------|---------------|
| P0 | Run health check | `bash scripts/library_health_v341.sh` |
| P1 | Optimize all v3.3.0 kernels | Load `optimize-kernel` skill per kernel |
| P2 | Wire trust_ladder_kernel requires | Add to R5 kernels via optimize-kernel |
| P3 | Wire memory_admission_kernel | Add to memory-writing skills/kernels |
| P4 | Decompose monolithic playbooks | Apply PLAYBOOKS_DOCTRINE §8 |
| P5 | Create eval fixtures | One fixture per new kernel in evals/datasets/ |

---

## Architecture Invariants (14 — machine-readable)

See AGENTS.md and KERNEL_DOCTRINE §3. All 14 invariants are enforced as kernel laws.
Any artifact violating an invariant is invalid.

---

## Open Unknowns (v3.4.1)

| ID | Description | Owner |
|----|-------------|-------|
| U-T1 | Default trust level on session start (L2 vs L3) | Igor decision |
| U-T2 | Trust level persistence across sessions | Not wired |
| U-M1 | semantic_score threshold (0.65) calibration | Not validated |
| U-M2 | L9 graph backend not yet selected | Architecture decision |
| U-H1 | Hydrator implementation language | Not yet selected |
| U-GAP-CONSENT | ADR-015 consent layer not yet harvested | Next harvest |

See full ADR harvest status: docs/architecture/identityos_adr_index.md


---

## Preserved non-regressive material from l9_playbook_commit_pack_v1.0.0(3).zip::l9_commit_pack/README.md

# L9 Commit Pack v1.0.0
## Operator: cryptoxdog | Date: 2026-06-10

This commit pack contains the fully L9-aligned playbook system, governance
infrastructure, skill library, and agent registry for the L9 portable_agent_runtime.

## Quick Start

```bash
# 1. Drop .l9/ into your L9 project root
cp -r .l9/ /home/user/workspace/l9_kit/

# 2. Register your Claude Code / MCP runtime against the governance hooks
#    Add to .claude/settings.json:
#    { "hooks": { "PreToolUse": [".l9/governance/hooks/PreToolUse.md"],
#                 "PostToolUse": [".l9/governance/hooks/PostToolUse.md"],
#                 "Stop": [".l9/governance/hooks/Stop.md"] } }

# 3. Validate a playbook spec
playbook validate .l9/playbooks/vendor-onboarding/playbook.yaml

# 4. Run against golden test suite
playbook test .l9/playbooks/vendor-onboarding/ --golden golden_tests/happy_path.jsonl

# 5. Deploy domain pack overlay
playbook deploy --domain-pack domain_packs/industrial-recycling-v1.yaml
```

## Directory Structure
```
.l9/
├── system/
│   └── l9-operating-contract.md       # Master behavioral policy
├── governance/
│   ├── L9_GOVERNANCE.md               # Governance contract
│   ├── acap-profile-template.yaml     # WEF ACAP 7-section template
│   └── hooks/
│       ├── PreToolUse.md              # 8-layer tool-call gate
│       ├── PostToolUse.md             # Output validation gate
│       └── Stop.md                    # Final quality gate
├── skills/
│   ├── INDEX.yaml                     # Skill registry
│   ├── governance-hooks/SKILL.md      # Hook templates
│   ├── agents-project-memory/SKILL.md # Kernel continuity memory
│   └── ops-recycling-compliance/SKILL.md  # GY compliance (custom)
├── playbooks/
│   ├── vendor-onboarding/
│   │   ├── playbook.yaml              # END-TO-END playbook spec
│   │   └── golden_tests/              # Regression test suite
│   ├── invoice-ar-processing/
│   │   └── playbook.yaml
│   ├── document-extraction/
│   │   └── playbook.yaml
│   └── multi-agent-routing/
│       └── playbook.yaml              # L9 master orchestrator
└── memory/
    ├── README.md
    └── global/
        └── conventions.md             # L9 naming conventions

l9_agents.yaml                         # Agent registry (grep-able)
domain_packs/industrial-recycling-v1.yaml  # GY domain overlay
CHANGELOG.md
```

## Disposition Map
| Playbook | Source | Disposition |
|----------|--------|-------------|
| vendor-onboarding | storious/agent-playbook + Frontier brief | FORK_AND_MODIFY |
| invoice-ar-processing | vasilyu1983 finance.payments skill | FORK_AND_MODIFY |
| document-extraction | vasilyu1983 document.pdf/docx skills | FORK_AND_MODIFY |
| multi-agent-routing | project-nova + madebyaris/agent-orchestration | FORK_AND_MODIFY |

## Governance Architecture
All playbooks operate under the bounded-autonomy control loop:
`PLAN → POLICY-CHECK → ACT → VERIFY → LOG → CONTINUE/ESCALATE`

Enforcement is at the platform hook layer (PreToolUse/PostToolUse/Stop),
NOT at the prompt layer. Policy cannot be overridden by LLM reasoning.


---

## Preserved non-regressive material from l9-ops-v1.2.2(3).zip::l9-ops/README.md

# l9-ops

> **v1.2.2** — fully wired. Run `make ci` to validate the whole system.

The governance operating model for L9 machine intelligence. Not a prompt library — the substrate every agent loads from, self-enforces against, and contributes back to.

## Architecture

```
l9-ops/
├── AGENTS.md                    # Session TOC — always loaded (≤150 lines)
├── MANIFEST.json                # Dependency graph + registry (v1.2.2)
├── WIRING.md                    # Connection contracts
├── Makefile                     # Single entry point for all operations
│
├── doctrines/                   # Governing standards (domain-agnostic)
│   └── universal_hardbans.md    # R0 bans — always active
│
├── kernels/optimized/           # 9 L9 kernels (three-tier structure)
├── skills/                      # 4 skills (SKILL.md standard)
├── playbooks/                   # 1 playbook (microservice-build, 3/17 steps)
├── prompts/                     # 2 prompts
│
├── evals/
│   ├── promptfooconfig.yaml     # 16 test stubs
│   ├── datasets/                # 16 eval fixture stubs
│   └── results/                 # promptfoo output (gitignored)
│
└── scripts/
    ├── add_artifact.py          # Atomic scaffolder + wirer
    ├── validate_wiring.py       # 9-dimension wiring validator
    ├── convergence_tracker.py   # Telemetry loop
    ├── impact_analysis.py       # Dep graph impact analysis
    ├── library_health.sh        # Health + stale detection
    ├── enforce_progressive_disclosure.sh
    └── audit_hardban_duplication.sh
```

## Adding a New Artifact

```bash
# Kernel
make add-kernel id=review_cycle_kernel.v1 name="Review Cycle" ring=R5 weight=1.0

# Skill  
make add-skill id=analyze-data name="Analyze Data" kernels="context_budget_kernel.v1"

# Playbook
make add-playbook id=data-pipeline name="Data Pipeline" kernels="execution_plan_kernel.v1"

# Prompt
make add-prompt id=gap-analysis-v1 name="Gap Analysis"

# Validate immediately
make validate-wiring id=<artifact-id>
```

## CI Gate

```bash
make ci     # health + disclosure + hardbans + impact + convergence + wiring
make eval   # promptfoo eval suite (requires ANTHROPIC_API_KEY)
make all    # ci + eval
```

## Post-Eval Write-Back

After running evals, record results to activate the convergence_footer telemetry loop:

```bash
python3 scripts/convergence_tracker.py \
  --update-kernel context_budget_kernel.v1 \
  --pass-rate 0.92 \
  --model claude-sonnet-4
```


---

## Preserved non-regressive material from l9_action_governor_pack(3).zip::l9_action_governor/README.md

# L9 Action Governor

## Endgame

L9 is a governance-native autonomous infrastructure layer. It reconstructs hidden system architecture, detects drift, evaluates operational readiness, and produces governed convergence plans.

The Action Governor is the missing decision component.

It consumes the outputs of an L9 run and converts them into ranked operational action:

```text
GovernanceGraphIR
+ governance scores
+ convergence plans
+ runtime findings
        ↓
L9 Action Governor
        ↓
ranked decisions
execution queue
remediation queue
escalation queue
rename plan
reorg plan
```

The Action Governor answers four questions every time:

1. What should be built?
2. What should be renamed or reorganized?
3. What should be remediated or escalated?
4. What should be deferred, archived, or deleted?

## Why merge repo topology, governance topology, and runtime topology?

They are not merged for neatness. They are merged because the Action Governor cannot rank action from one topology alone.

| Topology | What it knows | What it cannot know alone |
|---|---|---|
| Repo topology | Files, folders, modules, imports, docs, prompts, artifacts | Whether the artifact is governed or safe to act on |
| Governance topology | Rules, policies, gates, ownership, authority, escalation paths | Whether anything is actually broken in the repo |
| Runtime topology | Live failures, traces, findings, violations, usage signals | Whether the failure belongs to a strategic component or dead junk |

The unified `GovernanceGraphIR` gives one decision surface:

```text
what exists + what rules bind it + what is happening now
```

Without the merge, the system can analyze but cannot govern.

## MVP command

```bash
python -m l9_action_governor.cli decide examples/l9_runs/example_run --out /tmp/l9_decision
```

Output:

```text
ranked_decisions.yaml
execution_queue.yaml
remediation_queue.yaml
escalation_queue.yaml
rename_plan.yaml
reorg_plan.yaml
decision_report.md
```

## Decision classes

```yaml
decision_class:
  - build_now
  - build_next
  - build_later
  - remediate_now
  - escalate
  - rename
  - reorganize
  - archive
  - delete
  - defer
```

## Core rule

Every run must produce at least one ranked decision.

No decision means no value.


---

## Preserved non-regressive material from l9_playbook_commit_pack_v1.0.0(3).zip::l9_commit_pack/.l9/memory/README.md

# L9 Kernel Continuity Memory
## Source: danielmiessler/Personal_AI_Infrastructure#MEMORY/STATE/ + storious/agent-playbook#.agent/memory/

This directory stores durable agent memory across sessions.
All writes are append-logged with run_id, timestamp, and provenance.

## Directory Structure
```
.l9/memory/
├── global/
│   ├── conventions.md          # L9 naming/style conventions
│   ├── decisions.md            # Architectural decisions log
│   └── glossary.yaml           # Domain terminology
├── sessions/
│   └── <session_id>.json       # Per-session state (TTL: 7 days)
├── agents/
│   └── <agent_id>.json         # Agent-scoped durable facts
└── audit/
    └── chain.db                # Hash-chained audit log (SQLite)
```

## Access Rules
- Read: any L9 agent (read-only for global/)
- Write global/decisions.md: requires `acap_tier >= 3` + signed commit
- Write sessions/: any agent (own session only)
- Write agents/: only the owning agent

## Retention
| Namespace | TTL |
|-----------|-----|
| global/ | permanent |
| sessions/ | 7 days |
| agents/ | 90 days |
| audit/ | 7 years |


---

## Preserved non-regressive material from l9_action_governor_pack(3).zip::l9_action_governor/.pytest_cache/README.md

# pytest cache directory #

This directory contains data from the pytest's cache plugin,
which provides the `--lf` and `--ff` options, as well as the `cache` fixture.

**Do not** commit this to version control.

See [the docs](https://docs.pytest.org/en/stable/how-to/cache.html) for more information.


---

## Preserved non-regressive material from compliance_execution_command_center_packet(3).zip::compliance_execution_packet/README.md

# Compliance Execution Command Center Packet

This packet contains a company-agnostic Skill design for executing advisor-created compliance guides from canonical YAML profiles.

It is designed for matters like:

- tax compliance execution
- BOI filings
- annual reports
- court deadlines
- permit/license renewals
- nonprofit launch workflows
- CPA document collection
- regulatory filings

The agent executes the workflow, tracks state, stages forms, fills configured sensitive fields, uploads configured secure files, pays approved small fees, and stops at final human gates.

## Main artifact

`compliance-execution-command-center/`

## Key policy locks

- Upload passport/license: allowed when configured.
- Enter SSN/bank account: allowed when sourced from secrets.
- Payments USD 150 and under: allowed when configured and evidence logging is active.
- Final submit/certify/e-sign/court filing/legal-tax election/payment over USD 150: live human action required.

## Samples

- `samples/llc_1a_ty2025_profile.yaml`
- `samples/nonprofit_launch_profile.yaml`


---

## Preserved non-regressive material from canonical_persistent_cognitive_entity_stack_v1(3).zip::canonical_persistent_cognitive_entity_stack_v1/README.md

# Canonical Persistent Cognitive Entity Stack v1

## Objective

Create a canonical, user-agnostic architecture for a persistent cognitive entity that can move across substrates while preserving familiarity, memory, identity, behavior, permissions, and state continuity.

## Core Idea

```yaml
persistent_cognitive_entity:
  identity: persistent
  substrates: replaceable
  memory: governed
  behavior: kernel_constrained
  trust: permissioned
  state: portable
```

## Included

### Core Agent Stack
- identity layer
- psyche / behavioral layer
- relationship layer
- epistemic reality validation layer
- semantic language layer
- state routing layer
- operational layer
- evaluation layer

### Cross-Substrate Continuity
- portable identity contract
- substrate adapter schema
- trust permission ladder
- continuity handoff packet
- embodiment context schema

## Product Thesis

The adoption unlock for personal agents, robots, vehicles, browsers, and ambient AI is continuity.

Users integrate agents faster when the same familiar cognitive entity can inhabit multiple substrates.




