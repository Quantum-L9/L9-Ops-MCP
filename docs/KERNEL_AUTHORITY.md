# Kernel Authority Plane (Slice 1)

L9-Ops-MCP owns the **canonical context authority** boundary. Slice 1 of the
Kernel Authority consolidation adds a deterministic MCP surface that lets a
future PE consumer request kernel authority for a declared execution profile
and receive:

1. The exact canonical kernel artifact(s) selected.
2. Validated kernel metadata.
3. The exact content identity of every selected artifact.
4. Provenance sufficient to reproduce the resolution.
5. A bounded normative-context projection (Tier-1 only).
6. An aggregate deterministic `resolution_digest`.
7. Explicit failure when authority cannot be resolved safely.

This is **normative authority**. It is not memory search, it is not advisory
context, and it never consults Graphiti or an LLM.

## What `kernel_resolve` does

- Loads canonical kernel artifacts filtered to `docs/kernels/**` and tagged
  `kernels` in `AGENT_RETRIEVAL_INDEX.yaml`.
- Independently hashes each artifact and verifies against the index hash;
  mismatch → `KERNEL_DIGEST_MISMATCH`.
- Validates each parsed kernel against
  `schemas/kernel.canonical.schema.json`. Malformed kernels are retained in
  the registry (so their content identity is still discoverable) but refuse
  to be selected by the resolver.
- For a requested `profile`, walks the declared `requires` graph
  deterministically (dependencies before dependents; kernel-id tie-break).
- Enforces:
  - **Lifecycle** — `deprecated` or `archived` kernels fail closed;
    `experimental` requires explicit `allow_experimental=true`.
  - **Trust** — `ring` maps to the doctrine minimum trust level
    (R5 → L3, R4 → L2, etc.); insufficient trust fails closed.
  - **Budget** — the sum of selected `overload_weight` values must fit
    within the requested `max_overload_weight`.
- Projects a **Tier-1** normative context (`init.behavior`-equivalent plus
  `hard_bans` plus identity/provenance). Full Tier-2/Tier-3 doctrine is not
  emitted by default.
- Computes `resolution_digest = sha256(canonical_json(payload))`. Timestamps,
  packet IDs, host state, PID, mtime, and absolute checkout paths are
  deliberately excluded so the same request against the same repo state
  reproduces the same digest across processes.

## What `kernel_resolve` does not do

- It does not modify or consume Cursor-Governance or the PE `Program Lock`.
- It does not read Graphiti, memory, or any LLM.
- It does not perform semantic routing, fuzzy similarity, or embedding-based
  applicability decisions.
- It does not implement `requested_kernel_ids` (deferred from Slice 1).
- It does not enumerate the full R0-R4 baseline; profile → seed kernels →
  declared `requires` closure only.

## Determinism guarantee

For the same normalized request and the same repository state, resolution
produces the same selected authority and the same `resolution_digest`. This
holds across separate resolver instances and across separate processes. The
digest is computed with `canonical_json` (UTF-8, sorted keys at every level,
compact separators, `allow_nan=False`).

## Failure semantics

A failed resolution never looks like a successful empty context. The tool
returns a stable JSON error object with a machine-actionable `code` and a
human-readable `message`. Codes (from `src/l9_ops_mcp/kernel_models.py`):

| Code | Meaning |
|------|---------|
| `KERNEL_NOT_FOUND` | Kernel ID or path is unknown. |
| `KERNEL_SCHEMA_INVALID` | Registered kernel is not schema-conformant. |
| `KERNEL_INDEX_ENTRY_MISSING` | Retrieval index entry is missing required fields. |
| `KERNEL_DIGEST_MISMATCH` | Verified SHA-256 differs from the indexed SHA-256. |
| `KERNEL_DUPLICATE_ID` | Two canonical artifacts share a kernel_id. |
| `KERNEL_DEPRECATED` | Deprecated / archived kernel cannot load in Slice 1. |
| `KERNEL_EXPERIMENTAL_NOT_ALLOWED` | Experimental kernel without opt-in. |
| `KERNEL_TRUST_INSUFFICIENT` | Caller's trust level is below the ring minimum. |
| `KERNEL_DEPENDENCY_MISSING` | A required kernel is not registered. |
| `KERNEL_DEPENDENCY_CYCLE` | The requires graph contains a cycle. |
| `KERNEL_BUDGET_EXCEEDED` | Selected authority exceeds `max_overload_weight`. |
| `KERNEL_PROFILE_UNKNOWN` | Profile is not in `PROFILE_KERNELS`. |
| `KERNEL_CONFLICT` | Reserved for merge conflicts under future precedence rules. |
| `KERNEL_REQUEST_INVALID` | Request violated an input contract. |

## Profiles supported in Slice 1

| Profile | Seed kernel(s) | Notes |
|---------|----------------|-------|
| `BUILD` | `l9_build_kernel.v1` | Requires `l9_coding_kernel.v1` transitively. |

All other profile names return `KERNEL_PROFILE_UNKNOWN`. Slice 2 will add
CODING and any additional profiles required for the PE integration.

## Boundary with governed memory

`kernel_resolve` is normative authority. `memory_get_budget_slice` is
advisory / historical context. Neither substitutes for the other. Future
orchestration may combine them; Slice 1 keeps them cleanly separate.

## Boundary with TransportPacket

The transport envelope may carry the resolution as its payload, but
`resolution_digest` is the domain identity — not `TransportPacket.packet_id`.
Two transport packets may legitimately have different packet IDs while
carrying the exact same resolution digest.

## Testing

Slice 1 kernel tests run without Neo4j, Graphiti, AWS, Infisical, GitHub,
external MCP clients, or an LLM. They live in:

- `tests/test_kernel_registry.py` — discovery, hashing, schema, path safety.
- `tests/test_kernel_resolver.py` — profile, trust, budget, lifecycle, deps.
- `tests/test_kernel_determinism.py` — replay, subprocess replay, sensitivity,
  canonical JSON contract.
- `tests/test_kernel_index_and_projection.py` — real-repo index drift +
  Tier-1 projection bounds.
- `tests/test_kernel_mcp_tool.py` — MCP registration, happy/error paths,
  no-Graphiti-import architectural assertion.

Run: `pytest tests/test_kernel_*.py -q`.

## Residuals

- `docs/kernels/R0/soul_kernel.v1.yaml` and
  `docs/kernels/R5/preferences_kernel.v1.yaml` are canonical kernel artifacts
  today but omit doctrine-mandated fields (`version`, `title`, `purpose`,
  `activation_phase`, `status`, `overload_weight`, `hard_bans`). They are
  registered as `schema_valid=False` and cannot be selected. Slice 2 must
  either bring them up to canonical form or explicitly move them to a
  non-canonical documentation location.
- `PROFILE_KERNELS` currently supports only `BUILD`. Slice 2 will introduce
  a machine-readable profile registry that other consumers can extend
  without editing this module.
- `requested_kernel_ids` is defined on the request model but rejected in
  Slice 1. A later slice will bind it as a narrowing filter over the
  profile-applicable authority.
- Tier-2/Tier-3 progressive-disclosure levels are deferred; Slice 1 only
  emits Tier-1.
- The `mcp` SDK 2.0 removed the `FastMCP` surface. Slice 1 pins
  `mcp[cli]<2.0` and `tests/test_kernel_mcp_tool.py` skips loudly if a 2.x
  SDK is present. A later slice must migrate `src/l9_ops_mcp/server.py` to
  the new server surface before the pin can be lifted.
