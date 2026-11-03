---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs", "mcp", "context-control-plane", "graphiti", "governance"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.context.readme__md"
title: "README"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "README.md"
content_hash: "c0a3d5449524e07b150cb5f3ef732e80cd7d231884b9533cd265358ed47f24b5"
token_cost_estimate: 1435
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "auditor"
description: "Unknown"
activation_signals: ["validate", "build", "agent"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
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
- Expose MCP tools for budget-bounded context slices (governed memory plane) and for deterministic canonical kernel authority (kernel authority plane).
- Validate skills, playbooks, registries, pyproject entrypoints, and command wiring.
- Enforce the Quantum-L9 org invariant for upload-to-repo routing.

## Kernel Authority Plane

Slice 1 adds a `kernel_resolve` MCP tool that returns deterministic canonical
kernel authority for a declared execution profile. It never consults
Graphiti or an LLM. See [docs/KERNEL_AUTHORITY.md](docs/KERNEL_AUTHORITY.md)
for the full contract, error taxonomy, and determinism guarantee.

For the restricted Manus integration, see
[docs/MANUS_CONNECTOR.md](docs/MANUS_CONNECTOR.md). It exposes only
`kernel_resolve`, never the governed-memory plane.

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

## Repository Metadata Injector

The repository-local development tool is `l9-meta-injector` v4.3.0, pinned to
`Quantum-L9/l9-meta-injector` commit
`c53ef3aa0ccea04af2adfe67800ad09843b6e0fe` in `package.json`,
`package-lock.json`, and `.l9/meta-authority.yaml`. Node.js >=18 and GitHub
access to that repository are required; this does not alter the Python MCP
runtime or start a server.

```bash
make meta-setup
make meta-inventory
make meta-apply
make meta-check
```

The corresponding npm commands are `npm run meta:inventory`,
`npm run meta:apply`, and `npm run meta:check`. Inventory and check are
read-only observations. Apply injects actual YAML metadata headers into
eligible Markdown artifacts under authority `Quantum-L9`, with namespace
`L9-Ops-MCP`, and refreshes the tracked `.l9/metadata-index.jsonl`. The authority
uses `inline_managed` with `inline_allow: ["**/*.md"]`; document bodies and
existing legacy L9 metadata comments are preserved. The injector routes
executable/configuration formats and unsupported complex frontmatter through
the central index instead of adding unsafe inline headers. Normal modes
protect `SKILL.md`; no skill-description improvement or LLM mode is enabled.

After intentional changes to canonical Markdown kernel headers, update their
SHA-256 entries in `AGENT_RETRIEVAL_INDEX.yaml`, refresh non-canonical index
entries, then rerun apply and check so both indexes match the actual files.

Run apply after changing repository content, then check before committing.
The initial check before the first apply reports a missing index as drift;
later checks must exit zero. Keep the central index in Git. Installed
`node_modules/` and inventory reports in `.l9-meta-injector-out/` are ignored;
`.l9metaignore` also excludes secret files, virtual environments, and generated
outputs from artifact discovery while retaining `.env.example`. The installed
CLI prints its check/apply report location. Do not use the
injector checkout's legacy `npm run inventory`, which can annotate files.

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
