---
l9_schema: 1
artifact_type: documentation
tags: [ci-proof, repository-execution, governance]
retrieval: on_demand
status: active
---

# CI Proof Contract

CI is trusted only when it proves the repository instructions are runnable from a clean checkout. A workflow's existence, successful test collection, or a skipped validator is not execution proof.

## Organization admission

`.l9/repo-workflow.json` declares exactly:

```json
{
  "schema": "l9.repo-execution/v2",
  "facade": "make-v1",
  "required_phases": ["setup", "validate", "check", "test"]
}
```

The organization-owned runner validates this contract, verifies `Makefile` byte-for-byte against its released facade, and checks the unconditional `.PHONY` implementations in `Repo.mk` before running any phase. The repository cannot choose an enforcement mode or substitute its own Core validator. A typed failed result is blocking even if the analysis action's process returns zero to allow later analysis to finish.

`Makefile` was reconciled with `Quantum-L9/l9-ci-core` commit `1bc4df6910b932d82d70bded7b9edab5e5623fc6`, the immutable runner revision observed in the failing organization job. Regenerate it through that approved Core checkout's `RepositoryExecution(...).reconcile()` or its repository-execution reconcile CLI. Do not edit the generated file, add metadata headers, or redefine facade targets in `Repo.mk`.

## Required execution

| Phase | Repository-owned implementation | Blocking proof |
|---|---|---|
| `setup` | `repo-setup` | Create `.venv`; install `.[dev]` with all declared dependencies. |
| `validate` | `repo-validate` | Actual repository wiring and README/AGENTS/workflow command parity, including `Repo.mk`. |
| `check` | `repo-check` | Library health, progressive disclosure, hardban audit, actual declared-dependency impact, convergence, Ruff over `src scripts tests`, mypy over `src/l9_ops_mcp`. |
| `test` | `repo-test` | Execute the complete `tests` and `scripts` suites; collection is not a substitute. |

The governance workflow uses these same phases. `make ci` runs validate, check and test after setup and stops at the first failure. No Ruff or pytest failure is swallowed. Existing runtime/graph/PR-repair commands remain available through `Repo.mk`.

The L11 fast-test step also executes tests rather than returning success after `--collect-only`. Its full test and coverage jobs remain intact. Protected-file approval, CodeQL, SonarCloud, Semgrep and secrets scanning remain independent checks; repository tests do not replace them.

## Structural proof and manifest boundary

Wiring must inspect non-empty current repository evidence and fail on broken declared paths, invalid links, malformed declarations and unresolved dependencies. It must not fabricate a root `MANIFEST.json`, silently validate an empty registry, or treat historical `config/MANIFEST.json` pack provenance as the consolidated repository's runtime authority. See [WIRING.md](WIRING.md) for the implemented structural scope.

The required proof remains that scripts referenced by active automation exist, advertised Make commands resolve, Python scripts parse, console scripts resolve, and registered artifacts connect to their declared authorities. Structural proof does not certify doctrinal content quality, live Graphiti behavior, or successful LLM-assisted evals.

The operator explicitly approved marking the incomplete `microservice-build`
guide superseded on 2026-11-05. Its original 17-step description and unresolved
requirements remain preserved as historical material. Active use routes to the
existing `new-constellation-node` playbook, whose declared local files and
dependencies must validate. Supersession is not a claim that the old guide's
missing steps or five upstream kernels now exist; a broken replacement remains
a CI failure.

## Honest status and external tests

Use PASS, FAIL, BLOCKED, UNKNOWN, or NOT_APPLICABLE_WITH_REASON. Unknown or absent evidence must not be promoted into success.

The existing four live-Neo4j integration tests skip when `L9_NEO4J_URI` is absent. Offline kernel/MCP tests must still execute with the complete MCP dependency installed. This repair adds no skipped tests, exclusions or xfails. Live database and prompt-eval results must be claimed only after executing them in their authorized environments.
