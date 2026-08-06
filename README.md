---
l9_schema: 1
artifact_type: documentation
tags: [docs, mcp, context-control-plane, graphiti, governance]
retrieval: on_demand
status: active
---

# L9-Ops-MCP

**Quantum-L9 MCP Context Control Plane**

L9-Ops-MCP is the agent-facing MCP control plane for Quantum-L9 context discovery. It is not the durable memory module and it does not replace Graphiti. It injects and validates artifact metadata, bridges repo/file metadata to Graphiti, and exposes bounded context slices to agents through MCP.

## Operating Model

```text
repo files / uploads
  -> metadata injection
  -> artifact manifest + retrieval index
  -> graph bridge / export
  -> Graphiti / Neo4j
  -> L9-Ops-MCP server
  -> agent context slices over MCP
```

## Responsibilities

- Inject and validate canonical metadata on inbound files.
- Build artifact manifests, retrieval indexes, trace maps, and unknown registers.
- Bridge artifact metadata to Graphiti / Neo4j.
- Expose MCP tools for budget-bounded context slices.
- Validate skills, playbooks, registries, pyproject entrypoints, and command wiring.
- Enforce the Quantum-L9 org invariant for upload-to-repo routing.

## Non-Goals

- Do not own long-term semantic memory.
- Do not expose raw graph dumps to agents.
- Do not create repositories outside `Quantum-L9`.
- Do not accept pass-only validation claims.

## Quick Start

```bash
make help
make setup
make validate
make health
make skill-audit
make playbook-audit
make wiring
make ci
```

## Runtime Commands

```bash
make mcp-dev
make preflight
make graph-export
make graph-verify
make graph-sync
```

## CI Proof Contract

CI is meaningful only when it proves all referenced automation exists and runs from a clean checkout using declared dependencies. The governance workflow runs:

```bash
bash scripts/library_health.sh
bash scripts/enforce_progressive_disclosure.sh
bash scripts/audit_hardban_duplication.sh
python3 scripts/impact_analysis.py --all
python3 scripts/convergence_tracker.py
python3 scripts/validate_wiring.py --all
```

The wiring layer covers skill installability, playbook schema validity, AGENTS registry links, pyproject console scripts, README/Makefile parity, upload-to-repo routing, and Quantum-L9 org invariant enforcement.

## Layout

```text
.
├── AGENTS.md
├── README.md
├── Makefile
├── ORG_INVARIANTS.yaml
├── docs/
├── skills/
├── playbooks/
├── schemas/
├── scripts/
├── src/l9_ops_mcp/
├── tests/
└── evals/
```

The future `library/`, `runtime/`, and `governance/` split is intentionally deferred. This repo remains one working tree until those boundaries are stable.

## PR Lineage

PR #3 is the active Graphiti/MCP consolidation branch. PR #2 should be closed as superseded only after PR #3 or a new consolidation PR carries its functional lineage and CI proof gates. PR #1 remains separate as the graph export/import/sync adapter layer unless later rebased into the consolidation branch.

## First-Class Readiness Definition

This repo is first-class when README, AGENTS, Makefile, and CI agree; every referenced script exists and runs; every console script imports; every registered skill and playbook resolves; every repo birth route enforces `Quantum-L9`; and validation records honest PASS, FAIL, BLOCKED, UNKNOWN, or NOT_APPLICABLE_WITH_REASON outcomes.
