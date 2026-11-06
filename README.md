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
content_hash: "94c1022c60c548d79830984679674d9d7f97a5303e965fe7f68b1903478305e1"
token_cost_estimate: 1323
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

## Format-Safe Metadata Headers

Repository-local `l9-meta-injector` tooling is pinned to one immutable GitHub
commit in `package.json`, `package-lock.json`, and `.l9/meta-authority.yaml`.
This rollout is based on `main`, not on an earlier metadata PR. Node.js >=18
and GitHub access to the pinned dependency are required.

```bash
make meta-setup
make meta-inventory
make meta-apply
make meta-check
```

Apply uses explicitly authorized carriers: YAML frontmatter for eligible
Markdown and language-valid metadata comments for source, scripts, tests,
and supported configuration/control files. The renderer preserves document
bodies, shebangs, encoding declarations, and newline conventions. Check and
inventory are read-only. No LLM mode is enabled.

The [metadata header policy](docs/METADATA_HEADER_POLICY.md) and
`.l9/header-exceptions.yaml` declare generated, fixture, strict-format,
existing-frontmatter, and protected-skill exceptions. `inline_exclude` wins
over `inline_allow`; neither can override protected internal state or generated
lockfiles. Exception files remain byte-identical and use the central index,
existing native metadata, or an explicit generated/internal exemption.

After intentionally changing canonical kernel bytes, update their full-file
SHA-256 entries in `AGENT_RETRIEVAL_INDEX.yaml`; the refresh script will not
silently bless canonical drift. Then run the noncanonical retrieval refresh,
apply again to synchronize `.l9/metadata-index.jsonl`, and run both metadata
and retrieval checks. The Python MCP runtime is not started by these commands.

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
