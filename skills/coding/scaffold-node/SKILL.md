<!-- L9_META
id: scaffold-node
version: 1.0.0
author: platform
domain: coding
use_case: Scaffold a new L9 Constellation node compliant with l9_coding_kernel.v1 from spec
model_target: [claude-sonnet-4, claude-3-5-sonnet]
inputs:
  - name: node_spec
    type: NodeSpec handoff object or inline spec
    required: true
    description: node_id, actions, domain, priority_class, type (worker|orchestrator)
  - name: domain_spec_path
    type: file path
    required: false
    description: Path to domain spec YAML if node is domain-driven
expected_output: Complete node directory structure per Layer 10, ready to pip install and register
eval_status: pending
last_tested: "2026-06-17"
tool_bindings: [file_read, file_write, bash]
security_surface:
  file_access: read-write
  shell_access: true
  network_access: false
  credential_access: false
/L9_META -->

## scaffold-node

## Description

Use this skill when creating a new L9 Constellation node from scratch — to generate
the complete compliant node directory structure per `l9_coding_kernel.v1.md` Layer 10.

**Objective trigger**: new node creation, scaffold node, create constellation node,
new worker, new orchestrator.
**Surface trigger**: NodeSpec handoff object from `new-constellation-node` playbook
Step 02, or inline spec provided directly.
**Negative trigger**: Do NOT use to modify an existing node's structure. Do NOT use
to scaffold non-Constellation Python projects.

## Inputs

- `node_spec` (required): NodeSpec object with node_id, actions list, domain, priority_class, type
- `domain_spec_path` (optional): path to domain spec YAML if node is domain-driven

## Steps

1. **Load harness**: Confirm `l9_coding_kernel.v1.md` Layer 10 file structure contract is active.
2. **Validate node_spec**: node_id matches `^[a-z0-9][a-z0-9-]{0,62}$`, actions non-empty,
   priority_class in [P0,P1,P2,P3], type in [worker, orchestrator].
3. **Create root directory**: `{node_id}/`
4. **Create engine/**: `spec.yaml`, `handlers.py`, `boot.py`,
   `config/schema.py`, `config/loader.py`, `config/settings.py`,
   `compliance/prohibited_factors.py`, `utils/security.py`
5. **Write engine/spec.yaml**: Populated from node_spec. actions list, priority_class, type.
6. **Write engine/handlers.py**: Stub handlers for each action — using TransportPacket signature.
   L9_META header. register_all() function wiring all handlers.
7. **Write engine/boot.py**: Startup assertions skeleton (empty assertions list — to be filled).
8. **Write config/settings.py**: BaseSettings class with safety=True defaults.
9. **Write src/{package_name}/__init__.py**: version + __all__ only.
10. **Write src/{package_name}/config.py**: frozen Pydantic + lru_cache skeleton.
11. **Write src/{package_name}/errors.py**: base exception hierarchy.
12. **Write contracts/transport-packet.schema.json**: minimal required fields schema.
13. **Write tests/**: unit/, integration/, compliance/, performance/ directories with
    one skeleton test file each.
14. **Write AGENTS.md**: minimal AGENTS.md pointing to l9_coding_kernel.v1.md.
14. **Write pyproject.toml**: package name, version, python>=3.12, constellation_node_sdk dependency.
15. **Write Makefile**: `harness` target running validate_contracts + ruff + mypy + pytest.
16. **Add L9_META headers**: to every generated file.
17. **Output manifest**: list of all created files + next steps (register node, write domain logic).

## Outputs

- Complete `{node_id}/` directory structure per Layer 10 contract
- All files have L9_META headers
- All handlers have correct TransportPacket → TransportPacket signatures
- engine/spec.yaml populated from node_spec
- Manifest of created files + immediate next steps

## Tool Bindings

- `file_write`: create all node files
- `file_read`: read domain_spec_path if provided
- `bash`: create directory structure

## Security Notes

- Write access to current working directory only
- No shell execution beyond `mkdir` and file creation
- No network access required
- No credential access required
