# Step 03 — Scaffold Node

**Input**: Validated NodeSpec from Step 02
**Output**: ScaffoldResult (created file manifest)
**Skill**: scaffold-node
**Kernels active**: l9_coding_kernel.v1

## Action

1. Load `scaffold-node` skill.
2. Execute scaffold-node skill with the Validated NodeSpec as input.
3. Confirm all Layer 10 required files are created.
4. Confirm L9_META headers present on all files.
5. Confirm `engine/handlers.py` has correct TransportPacket handler signatures.
6. Confirm `engine/spec.yaml` populated from NodeSpec.

## Validation

Run `find {node_id}/ -type f | sort` — compare against Layer 10 required structure.
Every required file present. No missing directories.

## Failure Recovery

If scaffold-node creates incomplete structure, identify missing files and create them
manually following Layer 10 contract.

## Handoff

ScaffoldResult (file manifest) → Step 04 (write-domain-logic)
