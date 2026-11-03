---
id: "L9-Ops-MCP.playbook.playbooks_github_upload_capture_playbook__md"
title: "PLAYBOOK"
artifact_type: "playbook"
mcp_primitive: "tool"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "playbooks/github-upload-capture/PLAYBOOK.md"
content_hash: "817c2920ab31d76ee56cfbe0e8d3af212180921e8cfc6a576326ea642a47d3dd"
token_cost_estimate: 258
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "auditor"
description: "Unknown"
activation_signals: ["validate", "generate", "produce", "plan", "route"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: ["Upload cannot be inspected.", "Repo route requires owner outside Quantum-L9.", "Validation evidence cannot be produced.", "WRITE requested without explicit authorization."]
---
# GitHub Upload Capture Playbook

## Objective

Convert uploaded files and packs into validated metadata, graph-visible artifact records, and safe repo-routing decisions under the Quantum-L9 org invariant.

## Steps

1. Ingest uploads and compute upload manifest.
2. Extract archives and preserve source paths.
3. Inject or verify canonical metadata.
4. Generate artifact manifest and retrieval index.
5. Export artifact metadata to graph seed.
6. Apply Quantum-L9 org invariant gate.
7. Route to new repo, existing repo PR, feature branch, skill candidate, playbook candidate, archive-only, or reject.
8. Validate wiring and evidence artifacts.
9. Produce DRY_RUN plan or WRITE plan.

## Required Handoffs

- `handoffs/upload_manifest.schema.yaml`
- `handoffs/repo_route_decision.schema.yaml`
- `handoffs/context_slice_request.schema.yaml`

## Stop Conditions

- Upload cannot be inspected.
- Repo route requires owner outside Quantum-L9.
- Validation evidence cannot be produced.
- WRITE requested without explicit authorization.
