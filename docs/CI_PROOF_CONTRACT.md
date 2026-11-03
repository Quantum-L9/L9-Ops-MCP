---
id: "L9-Ops-MCP.context.docs_ci_proof_contract__md"
title: "CI PROOF CONTRACT"
artifact_type: "context"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/CI_PROOF_CONTRACT.md"
content_hash: "f84d4cde5716fe172383813d5d857009edb8795f38e514852e300b60515dbaa9"
token_cost_estimate: 186
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "legal"
description: "Unknown"
activation_signals: ["contract"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
---
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
