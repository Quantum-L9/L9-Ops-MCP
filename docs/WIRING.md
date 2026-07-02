---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
<!-- l9-ops WIRING.md | v1.2.2 | 2026-06-17 -->

# l9-ops Wiring Map

Authoritative map of how every system component connects. Update this whenever a new connection is added.

## The Enforcement Loop

```
                    Makefile
                    (make ci)
                        |
        ┌───────────────┼───────────────────┐
        ▼               ▼                   ▼
library_health.sh  enforce_disclosure.sh  audit_hardbans.sh
        |               |                   |
        ▼               ▼                   ▼
impact_analysis.py  convergence_tracker.py  validate_wiring.py
        |               |                   |
        ▼               ▼                   ▼
  MANIFEST.json    kernel YAML files    MANIFEST + skills + AGENTS.md
  dep graph        convergence_footer   all 9 dimensions
```

## Connection Contracts

| Connection | Source of Truth | Breaks If |
|-----------|-----------------|-----------|
| Kernel ID (canonical) | `kernelid:` field in YAML, snake_case | Renamed without updating MANIFEST |
| Kernel ID ↔ MANIFEST | `kernels.registry[].id` | Field mismatches yaml kernelid |
| Kernel file path | `kernels.registry[].file` | File moved without updating MANIFEST |
| Dep graph ↔ kernels | `dependencyGraph.skillsRequiringKernels` | References non-existent kernel |
| impact_analysis ↔ files | MANIFEST `file` field (NOT string munging) | `file` field absent or wrong |
| convergence_tracker ↔ kernels | `convergence_footer.lastRunDate` / `modelVersion` | Fields absent from kernel |
| Scripts ↔ CI | Makefile + governance.yml | Script renamed without updating Makefile |
| Doctrine ↔ artifacts | KERNEL_DOCTRINE.md / SKILLS_DOCTRINE.md | Schema drifts from doctrine |

## add_artifact.py Wiring Contract

When `add_artifact.py` is called, it wires EXACTLY these 5 locations:
1. File created (kernel YAML / SKILL.md / PLAYBOOK.md / prompt YAML)
2. `MANIFEST.json` registry entry + dependency graph entry
3. `AGENTS.md` table row
4. `evals/datasets/<id>-basic.yaml` eval fixture stub
5. `evals/promptfooconfig.yaml` test stub

All 5 must be consistent. `make validate-wiring id=X` verifies this.

## Runtime Load Order

1. `AGENTS.md` — always loaded (TOC, universal hard ban ref)
2. `doctrines/universal_hardbans.md` — R0, always active
3. Kernel Tier 1 — on activation check (Trigger Triad dispatch)
4. Kernel Tier 2 — on task confirm
5. Skill/Playbook — if task requires structured workflow
6. Kernel Tier 3 — ONLY in audit/governance context

## v1.2.2 State

- 9 kernels: all fully wired (tier markers, Trigger Triad, lastRunDate, MANIFEST, AGENTS.md, fixture, promptfoo)
- 4 skills: all fully wired
- 1 playbook: fully wired (3/17 steps authored)
- 2 prompts: fully wired
- Total: 16 artifacts, 0 wiring gaps
