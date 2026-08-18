---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# L9 Commit Pack Changelog

## v0.5.0 — Kernel Authority Slice 1 (2026-08-18)

### Added
- `src/l9_ops_mcp/kernel_models.py` — typed domain models for the kernel
  authority plane, stable error taxonomy, canonical resolution payload.
- `src/l9_ops_mcp/kernel_registry.py` — deterministic canonical kernel
  registry with retrieval-index SHA-256 verification, safe YAML+Markdown
  parsing, two-phase schema validation, duplicate detection, and path
  containment.
- `src/l9_ops_mcp/kernel_resolver.py` — profile-driven deterministic
  applicability with dependency-closure resolution, ring-based trust
  enforcement, overload budget, Tier-1 progressive-disclosure projection,
  and canonical `resolution_digest` computation.
- `kernel_resolve` MCP tool exposed alongside the four existing memory
  tools; memory-plane imports are lazy so kernel authority runs without
  Graphiti, Neo4j, or tiktoken.
- `docs/KERNEL_AUTHORITY.md` — plane documentation, error taxonomy,
  determinism guarantee, and Slice 1 residuals.
- `tests/test_kernel_*.py` — 46 new tests covering registry, resolver,
  determinism, MCP surface, index integrity, and Tier-1 projection bounds.

### Changed
- `schemas/kernel.canonical.schema.json` upgraded from a permissive
  "any mapping" schema to a canonical Draft 2020-12 contract aligned with
  `docs/KERNEL_DOCTRINE.md` §4.
- `pyproject.toml` adds `jsonschema>=4.20` as a runtime dependency.

### Preserved
- All four memory tools (`memory_get_budget_slice`, `memory_ingest_episode`,
  `memory_query_context`, `memory_invalidate_fact`) remain registered and
  callable with unchanged contracts.
- Cursor-Governance is not modified; PE is not integrated. Graphiti is
  not consulted for normative authority.

## v1.0.0 — 2026-06-10

### Added
- `.l9/system/l9-operating-contract.md` — master behavioral policy for all L9 nodes
- `.l9/governance/L9_GOVERNANCE.md` — governance contract (SOUL.md pattern)
- `.l9/governance/acap-profile-template.yaml` — WEF ACAP 7-section template
- `.l9/governance/hooks/PreToolUse.md` — 8-layer PreToolUse enforcement policy
- `.l9/governance/hooks/PostToolUse.md` — output validation and staging policy
- `.l9/governance/hooks/Stop.md` — final quality gate policy
- `.l9/skills/INDEX.yaml` — L9 skill registry (50+ namespace pattern)
- `.l9/skills/governance-hooks/SKILL.md` — hook templates (harvest: vasilyu1983)
- `.l9/skills/agents-project-memory/SKILL.md` — kernel continuity memory skill
- `.l9/skills/ops-recycling-compliance/SKILL.md` — GY recycling compliance skill (custom)
- `.l9/playbooks/vendor-onboarding/playbook.yaml` — vendor onboarding end-to-end
- `.l9/playbooks/invoice-ar-processing/playbook.yaml` — invoice AR processing end-to-end
- `.l9/playbooks/document-extraction/playbook.yaml` — universal document extraction
- `.l9/playbooks/multi-agent-routing/playbook.yaml` — L9 master orchestrator
- `.l9/playbooks/vendor-onboarding/golden_tests/` — regression test suite
- `.l9/memory/README.md` — kernel continuity memory layer documentation
- `.l9/memory/global/conventions.md` — L9 naming and style conventions
- `l9_agents.yaml` — declarative agent registry (project-nova agent.yaml pattern)
- `domain_packs/industrial-recycling-v1.yaml` — GY industrial recycling domain pack

### Harvest Sources
- `storious/agent-playbook` — workflow phase-gate and .agent/ directory pattern
- `danielmiessler/Personal_AI_Infrastructure` — 26-event hook system (PAI v5)
- `dujonwalker/project-nova` — agent.yaml registry + SOUL.md governance contract
- `vasilyu1983/AI-Agents-public` — SKILL.md library (hooks, payments, document, memory)
- `madebyaris/agent-orchestration` — resource-lock + shared-memory coordination pattern
- `Frontier-Grade-AI-Playbook-Architecture.md` — canonical PlaybookSpec schema v1.0
