# CI Proof Contract

CI is not trusted because a workflow exists. CI is trusted only when it proves the repo instructions are runnable from a clean checkout.

## Required Proofs

1. Every script referenced by GitHub Actions exists.
2. Every script referenced by Makefile exists.
3. Every command advertised in README or AGENTS exists in Makefile.
4. Python scripts parse successfully.
5. `pyproject.toml` console scripts import and resolve to callables.
6. Skills have installable structure.
7. Playbooks have entrypoints and valid handoff schemas.
8. Upload-to-repo routing enforces the Quantum-L9 org invariant.

## Required Status Vocabulary

- PASS
- FAIL
- BLOCKED
- UNKNOWN
- NOT_APPLICABLE_WITH_REASON

Pass-only reports are invalid.
