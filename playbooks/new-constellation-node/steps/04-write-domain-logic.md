---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# Step 04 — Write Domain Logic

**Input**: Scaffolded node directory from Step 03
**Output**: Implemented handlers with domain logic
**Skill**: None
**Kernels active**: l9_coding_kernel.v1

## Action

1. For each action in NodeSpec.actions:
   a. Open corresponding handler in `engine/handlers.py`
   b. Implement domain logic — reading from `packet.payload`, writing to derive() output
   c. Scope all data access to `packet.tenant.org_id`
   d. Raise explicit typed exceptions on validation errors — never return None
2. If node is domain-driven: load domain spec from `domains/{domain-id}/spec.yaml`
   into typed Pydantic model via `engine/config/loader.py`.
3. Add unit tests for each pure function added.
4. Add integration test for each handler (using real testcontainers driver if applicable).

## Validation

Every handler: returns TransportPacket, preserves lineage.root_id, preserves trace_id.
Run `python -m pytest tests/unit/ -q` — all unit tests pass.

## Failure Recovery

Handler returns wrong type → check derive() call, not raw dict return.
trace_id not preserved → add `header.trace_id` to derive() update dict.

## Handoff

Implemented node directory → Step 05 (run-ci)
