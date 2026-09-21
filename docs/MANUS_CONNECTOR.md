---
l9_schema: 1
artifact_type: documentation
tags: [manus, mcp, kernel-authority, security]
retrieval: on_demand
status: active
---

# Manus Kernel Authority Connector

The **`l9-ops-manus`** Custom MCP connector is a deliberately restricted stdio facade for the L9-Ops-MCP **kernel authority plane**. It exposes exactly one operation, `kernel_resolve`, and delegates to the existing deterministic resolver with strict on-disk integrity verification forced for every request.

## Boundary

The connector resolves canonical Tier-1 kernel authority for a declared execution profile. Each response contains selected kernel identities, verified SHA-256 provenance, a bounded normative-context projection, and a deterministic `resolution_digest`. Failures use the native stable `{status: "error", code, message}` envelope.

The connector does **not** expose the native server's Graphiti-backed memory tools. It has no secret retrieval, shell execution, filesystem-write, deployment, repository-write, network, Graphiti, Neo4j, or durable-memory capability. The native server's broader MCP surface must not be registered as a Manus connector.

## Local command

Install the package and invoke the restricted module entry point:

```bash
uv sync --extra dev
python -m l9_ops_mcp.manus_kernel_server
```

The connector must be registered as a local stdio server using the checkout's
locked Python interpreter with arguments `-m l9_ops_mcp.manus_kernel_server`.
Set `L9_OPS_MCP_REPO_ROOT` to the immutable L9-Ops-MCP checkout that contains
the canonical kernel retrieval index. No credential or secret environment
variable is required.

## Verification

After registration, confirm that tool discovery lists **only** `kernel_resolve`, then run a bounded BUILD resolution:

```bash
manus-mcp-cli tool list --server l9-ops-manus
manus-mcp-cli tool call kernel_resolve --server l9-ops-manus --input '{"profile":"BUILD","consumer":"Manus","objective":"Resolve canonical build authority","trust_level":"L3","max_overload_weight":6.0}'
```

The current Slice 1 resolver supports only the `BUILD` profile. Unsupported profiles and insufficient trust levels must return a stable error rather than silently degrading authority.
