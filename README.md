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
make check
make test
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

The advertised `l9-preflight` console entrypoint delegates to the existing
eight-gate `scripts/preflight.sh`. Editable installs detect the checkout;
wheel installs outside a checkout must pass `l9-preflight --repo /path/to/repo`.
Invocation performs the existing live Graphiti/Neo4j smoke checks. CI verifies
that the entrypoint resolves, but does not claim those live checks were run.

## CI Proof Contract

The organization Core runner requires `.l9/repo-workflow.json` with the exact
`l9.repo-execution/v2` contract and `make-v1` facade. `Makefile` is generated
byte-for-byte by Core; repository commands and phase implementations live in
`Repo.mk`. Do not edit the generated facade or inject a header into it.

`make setup` creates `.venv` and installs the complete declared `.[dev]`
dependencies. Subsequent commands select `.venv/bin/python` automatically.
The governance workflow and organization Core run the same four phases:

```bash
make setup
make validate
make check
make test
```

`validate` checks current repository wiring and command parity, including
`Repo.mk` and both workflow extensions. `check` runs library health,
progressive disclosure, hardban auditing, declared-dependency impact,
convergence, Ruff and the strictly typed MCP package's mypy check. `test`
executes all product and L11 tests, not collection alone. Every phase propagates
failure; `make ci` runs the same three verification phases after setup.

The wiring and impact commands use the consolidated repository's actual
registries. The historical `config/MANIFEST.json` is retained as upstream pack
provenance, not promoted to an invented root manifest or used to claim that
zero artifacts were validated. See [docs/WIRING.md](docs/WIRING.md) for scope
and [docs/CI_PROOF_CONTRACT.md](docs/CI_PROOF_CONTRACT.md) for proof boundaries.

The incomplete historical `microservice-build` guide is superseded, not
certified as an implemented 17-step pipeline. Active node-build work uses the
existing [new-constellation-node playbook](playbooks/new-constellation-node/PLAYBOOK.md).
Its declared steps and dependencies must pass wiring validation; the old guide
and its unresolved requirements are retained for provenance.

## Layout

```text
.
├── AGENTS.md
├── README.md
├── Makefile
├── Repo.mk
├── .l9/repo-workflow.json
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
