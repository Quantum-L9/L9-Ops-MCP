<!-- L9_META
l9_schema: 1
origin: l9-kernel
layer: [agent-rules, kernel, cursor]
tags: [L9_KERNEL, agent-rules, cursor, transportpacket, constellation, harness]
owner: platform
status: active
canonical_path: docs/kernels/R5/l9_coding_kernel.v1.md
version: 3.3.0
last_tested: "2026-06-17"
eval_status: pending
overload_weight: 2.0
ring: R5
load_condition: "code_generation OR handler_authoring OR constellation_node OR write_python OR coding OR api_design OR node_build OR code_review"
requires: []
amplifies: [l9_build_kernel.v1, eval_harness_kernel.v1, sandbox_isolation_kernel.v1]
single_source_rule: "NEVER copy this file. Reference by path only. One version. No forks."
/L9_META -->

## TIER 1 — CAPABILITY DECLARATION

**capability**: Enforces the complete L9 Constellation TransportPacket wire contract, routing laws,
handler interface, authority boundaries, security, observability, replay/audit, file structure,
CI enforcement gates, and testing contract for all L9 Constellation nodes.

**use_when**: Any code generation, handler authoring, node build, constellation node work,
Python writing, API design, L9 engine build, or code review task involving L9 codebases.

**do_not_use_when**: Non-L9 codebases, infrastructure-only tasks (Dockerfile/Terraform only with no
engine code), documentation-only sessions with zero code generation.

**hard_bans**:
- MUST NOT import PacketEnvelope as an active contract anywhere
- MUST NOT create node-to-node calls (LAW-R2)
- MUST NOT mutate TransportPacket in place (LAW-T5)
- MUST NOT add print() anywhere — CI fails (Layer 14)
- MUST NOT use eval(), exec(), compile(), pickle.loads() (LAW-S2)
- MUST NOT resolve tenant context in engine — read from packet.tenant.org_id only
- MUST NOT add FastAPI routes, APIRouter, or app factories in engine files
- MUST NOT redefine trace propagation or replace inbound trace_id
- MUST NOT copy this file into any other location — reference by canonical path only

---

## TIER 2 — OPERATIONAL RULES

# ============================================================================
# L9 KERNEL CODING STACK — CONSTELLATION NODE
# ============================================================================
# TransportPacket is the ONLY wire format. PacketEnvelope is dead. No fallback.
# Violate any law → revert and ask.
# Source of truth: constellation_node_sdk contracts + L9 SSOT specs
# ============================================================================

## 0. PACKET CONTRACT AUTHORITY (read this first)

```
CANONICAL PACKET:   TransportPacket
SUPERSEDED:         PacketEnvelope, AgentPacket, raw_execute_dict
EXCLUSIVITY:        absolute — no alternate envelopes anywhere in core paths
SOURCE OF TRUTH:    constellation_node_sdk (transport/models.py, transport/packet.py)
```

Any file importing `PacketEnvelope` as an active contract **must be rejected at review**.
The build **must fail** if a PacketEnvelope import exists in a TransportPacket-native repo.

---

## 1. SYSTEM IDENTITY

| Property | Value |
|---|---|
| **Architecture era** | TransportPacket (post-migration) |
| **Wire format** | `TransportPacket` — only |
| **Birth dependency #1** | `constellation_node_sdk` — always, no exceptions |
| **Egress law** | All follow-up work routes to Gate via `GateClient.send_to_gate(packet)` |
| **Node type** | runtime (execution-only) OR orchestrator (workflow authority) |
| **Ingress** | `POST /v1/execute` and `GET /v1/health` — only |
| **Handler signature** | `async def handler(packet: TransportPacket) -> TransportPacket` |
| **Node name format** | `{domain}-{function}` — lowercase, hyphenated |
| **Registration** | `POST {GATE_URL}/v1/admin/register` from `engine/spec.yaml` |

This node is a **Constellation node only**. HTTP surface, auth, tenant resolution, logging config,
metrics, rate limiting, Docker/CI/Terraform, and envelope validation are **SDK + chassis concerns —
never engine concerns**.

---

## 2. LAYER 0 — TRANSPORT CONTRACT (non-negotiable)

### LAW-T1 — TransportPacket Only
- There is **exactly one** wire format: `TransportPacket`
- Do NOT introduce alternate packet types, legacy request adapters, or dict-first fallback paths
- Any compatibility with legacy formats belongs **outside** the core SDK and **never** in node code

### LAW-T2 — Handler Contract
```python
async def handler(packet: TransportPacket) -> TransportPacket:
    ...
```
- Tenant context is read from `packet.tenant.org_id` — never resolved by the engine
- Response packet MUST be built via `packet.derive(...)` — never mutated in place
- Every handler registered in `engine/handlers.py` ONLY

### LAW-T3 — Gate-Only Egress
- Nodes MUST only send follow-up work to `GATE_URL`
- Forbidden: peer node URLs, direct node-to-node dispatch
- Allowed: `GateClient.send_to_gate(packet)`
- Follow-up packets MUST set `provenance.origin_kind = "node"` and `address.destination_node = "gate"`

### LAW-T4 — Semantic vs Observational Change
```python
child    = packet.derive(update={...})   # semantic: new packet_id, hashes recomputed
observed = packet.with_hop(hop_entry)    # observational: transport_hash UNCHANGED
```

### LAW-T5 — Immutability
- `TransportPacket` is immutable — no in-place mutation
- ALL structural changes use `model_copy(update=...)` or `derive()`

### LAW-T6 — Transport Hash Stability
- `transport_hash` = SHA-256 of: header + address + tenant + payload + governance + provenance + delegation_chain + lineage + attachments + payload_hash
- `hop_trace` is **excluded** from `transport_hash` and is **append-only**

### LAW-T7 — Schema Validation Before Execution
- Schema validation happens **before** any handler executes
- No legacy dict coercion in Gate or runtime
- Schema source: `contracts/transport-packet.schema.json`

---

## 3. LAYER 1 — ROUTING LAW (non-negotiable)

### LAW-R1 — Gate Is Routing Authority
- Nodes express intent by `action` only — Gate resolves `action → destination`
- NEVER add code that resolves `action → worker URL` inside a node
- NEVER bypass Gate routing or cache peer routing outside Gate

### LAW-R2 — Node-to-Node Calls: Forbidden
```
ALLOWED:   client → gate, node → gate, gate → node
FORBIDDEN: node_a → node_b, orchestrator → worker_direct, worker → worker
```

### LAW-R3 — Node-Origin Packet Requirements
```python
provenance.origin_kind          = "node"
provenance.resolved_by_gate     = False
provenance.original_source_node = LOCAL_NODE_NAME
address.source_node             = LOCAL_NODE_NAME
address.destination_node        = "gate"
```

### LAW-R4 — No Peer Awareness
- Workers MUST NOT know peer URLs
- No private node registry inside runtime nodes
- No hardcoded peer dispatch

---

## 4. LAYER 2 — AUTHORITY BOUNDARY (non-negotiable)

### Gate (workflow-stateless transport authority)
- **Owns**: routing, admission, resilience decisions
- **Allowed state**: node_registry_cache, circuit_breaker_state, rate_limiter_state, idempotency_state — all bounded, discardable
- **Forbidden**: workflow decisions, decomposition, branching logic, workflow DAG storage

### Orchestrator (workflow authority)
- **Owns**: workflow DAG, step state, execution history, replay state, compensation state
- All sub-task dispatch routes **back through Gate** via SDK transport boundary
- **Forbidden**: direct node calls, embedded routing logic, gate bypass

### Runtime Node (execution-only)
- **Owns**: execution-local state, caches, model/session state
- **Forbidden**: routing, workflow branching, next-step decisions, direct node calls
- Handler receives packet, executes capability, returns result packet — nothing more

---

## 5. LAYER 3 — TRANSPORT PACKET FIELD CONTRACT

### Required Header Fields
```python
header.packet_id       # UUID
header.packet_type     # request|response|event|command|delegation|failure|replay_request|replay_response|compensation
header.action          # ^[a-z0-9][a-z0-9-]{0,63}$ — lowercase, explicit
header.priority        # int 0-3
header.created_at      # ISO 8601 datetime
header.timeout_ms      # int >= 1
header.schema_version  # str
header.retry_count     # int >= 0
header.replay_mode     # bool
```

### Required Address Fields
```python
address.source_node       # str
address.destination_node  # str
address.reply_to          # str
```

### Required Tenant Fields
```python
tenant.actor        # str — who is acting
tenant.on_behalf_of # str — who authorized
tenant.originator   # str — who started the chain
tenant.org_id       # str — tenant isolation key
```

### Required Security Fields
```python
security.payload_hash      # SHA-256 hex of canonical payload JSON
security.transport_hash    # SHA-256 hex of stable packet core (excludes hop_trace)
security.classification    # public|internal|confidential|restricted
security.encryption_status # plaintext|encrypted|envelope_only
security.pii_fields        # list
```

### Required Governance Fields
```python
governance.intent             # str
governance.compliance_tags    # list
governance.retention_days     # int
governance.redaction_applied  # bool
governance.audit_required     # bool
```

### Required Provenance Fields
```python
provenance.origin_kind       # client|node|gate
provenance.requested_action  # str
provenance.resolved_by_gate  # bool
```

### Lineage
```python
# Root: lineage.parent_id=None, generation=0, root_id=header.packet_id
# Child via derive(): lineage.parent_id=parent.packet_id, root_id=parent.lineage.root_id, generation+=1
```

### Response Contract
- MUST be a `TransportPacket`; reverse address direction; carry result in payload
- Preserve `lineage.root_id` and `header.trace_id`

---

## 6. LAYER 4 — NODE BIRTH CONTRACT

### Birth Stack (install in sequence)
```
1. constellation_node_sdk   ← ALWAYS — TransportPacket, GateClient, handlers, health, metrics
2. constellation_ingest     ← if node reads files or repos
3. constellation_obs        ← (future) structured telemetry
4. constellation_store      ← (future) storage adapters
5. constellation_auth       ← (future) extended auth
6. domain-<name>            ← the node's actual business logic
```

### Birth Acceptance Gate (every new package must pass)
```
1. pip install <package>   → succeeds in clean venv
2. from <package> import X → works with zero config
3. config loaded from env  → safe defaults, no crash if optional vars absent
```

### Birth Dependency Rules
- No import-time side effects
- No required env vars at import
- No heavy startup cost
- No assumptions about other packages present

---

## 7. LAYER 5 — NODE REGISTRATION CONTRACT

### Spec File (engine/spec.yaml)
```yaml
node:
  id: {node-name}           # lowercase, hyphenated
  actions:
    - action-name-one
    - action-name-two
  internal_url: http://{id}:8000
  priority_class: P2        # P0-P3
  max_concurrent: 50
  health_endpoint: /v1/health
  timeout_ms: 30000
  version: "1.0.0"
  type: worker              # worker | orchestrator
```

### Registration Wire Call
```
POST {GATE_URL}/v1/admin/register?overwrite=true
{ "{node-id}": { "internal_url": "...", "supported_actions": [...], "priority_class": "P2",
  "max_concurrent": 50, "health_endpoint": "/v1/health", "timeout_ms": 30000,
  "metadata": { "version": "1.0.0", "type": "worker" } } }
```

### Registration Rules
- `supported_actions` must be non-empty — build fails if empty
- Node IDs and actions normalized to lowercase

---

## 8. LAYER 6 — HANDLER INTERFACE

```python
# engine/handlers.py — THE ONLY file that bridges engine to SDK
from constellation_node_sdk import register_handler
from constellation_node_sdk.transport.models import TransportPacket

def register_all() -> None:
    register_handler("action-name", handle_action_name)

async def handle_action_name(packet: TransportPacket) -> TransportPacket:
    tenant_id = packet.tenant.org_id
    trace_id  = packet.header.trace_id   # preserve — do NOT generate your own
    payload   = packet.payload

    # ... domain logic ...

    return packet.derive(update={
        "header":  {"packet_type": "response"},
        "address": {"source_node": "this-node",
                    "destination_node": packet.address.source_node,
                    "reply_to": packet.address.source_node},
        "payload": {"result": ..., "status": "success"},
    })
```

### Handler Rules
- `engine/handlers.py` is the ONLY engine file that imports SDK transport code
- Handler MUST NOT configure logging, Prometheus, or tracing — inherited from SDK
- Handler MUST NOT generate its own `trace_id`
- Handler MUST use `logging.getLogger(__name__)` only
- Handler MUST fail closed — raise explicit exceptions, never coerce silently
- Every data access scopes to `packet.tenant.org_id` — no cross-tenant reads

---

## 9. LAYER 7 — SECURITY CONTRACT

### LAW-S1 — Fail Closed
- Transport violations raise explicit errors — never silently coerce invalid state
- Error messages must not expose secrets, PII, or internal topology

### LAW-S2 — Injection Prevention
```python
# CORRECT
label = sanitize_label(spec.target_node)  # regex: ^[A-Za-z_][A-Za-z0-9_]*$
# BANNED — no exceptions
eval(expression) / exec(code) / compile(code) / yaml.load(stream)
```

### LAW-S3 — PII Handling
- PII fields declared in `spec.compliance.pii.fields`
- Engine NEVER logs PII values
- `security.pii_fields` on every TransportPacket

### LAW-S4 — Signing
- Signs `transport_hash`; `signature` and `signature_algorithm` both set or both absent
- Algorithms: `hmac-sha256` or `ed25519` — NEVER hide signature failures

### LAW-S5 — Classification
- Every packet: `security.classification` = public|internal|confidential|restricted
- Never downgrade classification in a derived packet

---

## 10. LAYER 8 — OBSERVABILITY CONTRACT

### SDK Owns (do NOT redefine)
- Trace context extraction/injection, span creation at transport boundaries,
  transport metrics, hop timing, propagation consistency

### Node Must NOT
- Redefine trace propagation semantics
- Replace a valid inbound `trace_id`
- Fork a new trace for the same workflow hop
- Use telemetry as a hidden control plane

### Trace Field Rules
```python
header.trace_id    # REQUIRED — preserved across derive()
header.span_id     # optional — may change only at new execution boundary
header.trace_flags # optional — preserved if present
header.tracestate  # optional — preserved if present
```

### Structured Logging Rules
- No `print()` — build fails
- Bind context at packet entry: trace_id, tenant_id, action, node_name
- NEVER log: api_key, secret, password, token, raw_response, llm_response, partner_data, PII values

### Required Spans
```
gate_ingress, gate_dispatch, node_receive, node_handler, node_emit
```

### Minimum Log Context Per Entry
```python
{"trace_id": ..., "tenant_id": ..., "action": ..., "node_name": ..., "timestamp": ..., "level": ...}
```

---

## 11. LAYER 9 — REPLAY AND AUDIT CONTRACT

### Replay Store
- Every incoming `TransportPacket` recorded **before** handler executes
- Replay entries **immutable after write**
- Store `payload_hash` and `result_hash` — NOT raw payload
- Divergence on replay MUST be reported

### Replay Entry Required Fields
```python
entry_id, packet_id, action, tenant_id, payload_hash, result_hash,
recorded_at, node_name, l9_core_version, replay_count
```

### Audit Events
- Append-only — no update or delete paths
- Required: event_id, trace_id, node_name, action, tenant_id, outcome, payload_hash, timestamp, l9_core_version
- `outcome`: success | failure | rejected
- NEVER include raw payload, API keys, partner data, or secrets

### Workflow Replay (orchestrator only)
- MUST NOT reuse old packet IDs, bypass Gate, or mutate historical packets

---

## 12. LAYER 10 — FILE STRUCTURE CONTRACT

```
{node-name}/
├── engine/
│   ├── spec.yaml              # Node registration + actions + metadata
│   ├── handlers.py            # ONLY file bridging engine ↔ SDK
│   ├── boot.py                # Startup assertions
│   ├── config/
│   │   ├── schema.py          # Pydantic models for domain spec YAML
│   │   ├── loader.py          # YAML → DomainSpec typed model
│   │   └── settings.py        # Feature flags (all bool, safety=True default)
│   ├── [domain modules]       # gates/, scoring/, traversal/, sync/, gds/, graph/
│   ├── compliance/
│   │   └── prohibited_factors.py
│   └── utils/
│       └── security.py        # sanitize_label(), safe dispatch tables
├── domains/{domain-id}/spec.yaml
├── tests/
│   ├── unit/                  # Pure functions, gate compilation, scoring math
│   ├── integration/           # Real driver (testcontainers) — NEVER mock driver
│   ├── compliance/
│   └── performance/
├── contracts/transport-packet.schema.json
├── src/{package_name}/
│   ├── __init__.py
│   ├── config.py
│   ├── errors.py
│   └── py.typed
├── pyproject.toml
├── AGENTS.md
├── Makefile
└── .pre-commit-config.yaml
```

### File Structure Rules
- MUST NOT create new top-level directories without architectural approval
- MUST NOT create `engine/api/`, `engine/middleware.py`, or any SDK/chassis file
- Infrastructure (Dockerfile, docker-compose, CI, Terraform) lives in `l9-template` — never engine

---

## 13. LAYER 11 — CODE STANDARDS

```
Python 3.12+
Type annotations: required on all public functions
Prefer explicit, readable code — no clever one-liners in protocol code
Functions: single-purpose
```

### Error Handling
```python
# CORRECT
raise TransportValidationError(f"Missing required field: {field!r}")
# BANNED
return None   # on validation failure
pass          # swallowing transport violations
```

### Naming
- All Pydantic model fields and YAML spec keys: `snake_case`
- Python attribute name IDENTICAL to YAML key — no aliases, no camelCase
- All node IDs and actions: normalized to lowercase

### Feature Flags
```python
class Settings(BaseSettings):
    enable_experimental_feature: bool = False  # experimental → default False
    enforce_compliance_check: bool = True       # safety → default True
```

### Banned Patterns (absolute)
```python
eval(expression)
exec(code)
compile(code)
yaml.load(stream)                      # use yaml.safe_load
raise NotImplementedError              # ship code or DEFERRED.md entry
requests.post(node_url, json=raw_dict) # raw node-to-node call
httpx.post(peer_url, ...)              # direct peer dispatch
```

---

## 14. LAYER 12 — L9_META HEADER CONTRACT

Every tracked file MUST carry an `L9_META` header (Python/YAML/Markdown variants shown in
docs/HARNESS_DOCTRINE.md). Required fields: l9_schema, origin, layer, tags, owner, status.

---

## 15. LAYER 13 — TESTING CONTRACT

### Required Test Scope
```
Unit:        pure functions, gate compilation, scoring math, packet derive()/with_hop() invariants,
             transport hash stability, lineage correctness
Integration: real driver (testcontainers) — NEVER mock the data driver
             full handler execution, gate-client round-trip, idempotency, replay identity
Compliance:  prohibited factors blocked at compile time, PII not in logs, no PacketEnvelope imports
Performance: p95 latency target declared per domain in spec.yaml
```

### Test Patterns
```python
from constellation_node_sdk.transport.packet import TransportPacket
result = await handle_my_action(build_test_packet(action="my-action"))
assert isinstance(result, TransportPacket)
assert result.header.packet_type == "response"
assert result.lineage.root_id == original_packet.lineage.root_id
```

---

## 16. LAYER 14 — CI ENFORCEMENT

### Build Must Fail If
```
PacketEnvelope imports exist
direct node-to-node calls exist
raw HTTP posts to /execute bypass GateClient
runtime contains workflow logic
gate contains workflow state
orchestrator bypasses gate
non-TransportPacket execute path exists
packet mutation without derive() or with_hop()
handler signature is not TransportPacket → TransportPacket
transport_packet schema validation missing
node registration supported_actions is empty
trace_id missing on inter-node transport packets
trace_id not preserved across derive()
valid inbound trace_id replaced without policy
print statements exist anywhere
forbidden log fields emitted (api_key, secret, password, token, raw_response, llm_response)
counter metrics use unbounded label dimensions
direct agent-to-agent channels exist
replay entries mutate in place
audit emitter exposes update or delete path
```

### Required CI Checks
```
transport_packet_schema_validation
routing_policy_architecture_tests
no_packetenvelope_scan
gate_statelessness_checks
orchestrator_workflow_authority_checks
runtime_execution_only_checks
gate_client_only_execute_entry_check
node_registration_contract_validation
hop_trace_and_lineage_tests
idempotency_and_replay_tests
transport_trace_propagation_tests
replay_immutability_tests
audit_append_only_tests
forbidden_log_field_tests
```

### Validation Workflow Before Merge
```bash
python -m pip install -e ".[dev]"
python scripts/validate_contracts.py
python scripts/generate_schema.py
ruff check src tests scripts
mypy src
pytest -q
```

---

## 17. LAYER 15 — DOMAIN SPEC CONTRACT

### spec.yaml Structure
```yaml
domain:
  id: {domain-id}
  name: {Human Name}
  version: {major}.{minor}.{patch}-{stage}
ontology:
  nodes: []
  edges: []
traversal:
  steps: []
gates: []
scoring:
  dimensions: []
  aggregation: additive
sync:
  endpoints: []
gds_jobs: []
compliance:
  prohibited_factors: []
  pii:
    fields: []
    handling: hash
```

### Rules
- ALL behavior derives from YAML specs parsed into typed Pydantic models — no raw dicts for logic
- MUST NOT hardcode domain-specific values in engine logic
- Version: `{major}.{minor}.{patch}-{stage}` — no "latest", no dates
- Stages: seed | discovered | inferred | proposed | reviewed | production
- `gate.null_behavior` = "pass" | "fail" — REQUIRED per gate, no global default

---

## 18. QUICK REFERENCE — WHAT NOT TO BUILD

```
❌ PacketEnvelope imports anywhere         → TransportPacket only (LAW-T1)
❌ Alternate packet types or envelopes     → TransportPacket only (LAW-T1)
❌ dict-first fallback in runtime or gate  → TransportPacket only (LAW-T1)
❌ Direct node-to-node calls               → Gate-only egress (LAW-T3, LAW-R2)
❌ Peer node URLs in node runtime          → Gate-only egress (LAW-T3)
❌ In-place packet mutation                → derive() or with_hop() (LAW-T4, LAW-T5)
❌ Custom transport routing in node        → Gate is routing authority (LAW-R1)
❌ Tenant resolution in engine             → read from packet.tenant.org_id (LAW-T2)
❌ FastAPI routes, APIRouter in engine     → SDK owns ingress (Layer 6)
❌ structlog.configure(), basicConfig()    → inherited from SDK (Layer 8)
❌ generate own trace_id                   → inherited from SDK (Layer 8)
❌ print() anywhere                        → CI fails (Layer 14)
❌ eval(), exec(), compile()               → banned (Layer 11)
❌ yaml.load() without SafeLoader          → use yaml.safe_load
❌ raise NotImplementedError               → zero-stub protocol
❌ TODO/PLACEHOLDER without DEFERRED.md   → zero-stub protocol
❌ Dockerfile, CI, Terraform in engine     → l9-template owns infra (Layer 10)
❌ New top-level dirs without approval     → fixed file structure (Layer 10)
❌ Files without L9_META header            → CI fails (Layer 12)
❌ workflow logic in Gate                  → Gate is workflow-stateless (Layer 2)
❌ workflow DAG in runtime node            → orchestrator only (Layer 2)
❌ replay authority in runtime node        → orchestrator only (Layer 9)
❌ audit events with update/delete paths   → append-only (Layer 9)
❌ raw_response / llm_response in logs     → forbidden log fields (Layer 8)
```

---

## 19. TRANSPORT PACKET ANTI-PATTERNS (hard failures)

```
direct_node_calls
in_place_packet_mutation
multiple_transport_schemas
raw_http_execute_calls_with_untyped_dicts
PacketEnvelope_as_active_contract
node_local_private_transport_formats
mixed_transport_models
hardcoded_peer_dispatch
routing_based_on_private_network_map
special_case_orchestrator_bypass
semantic_routing_inside_gate_facing_transport_helpers
redefining_trace_propagation_in_application_code
using_telemetry_as_hidden_control_plane
```

---

## 20. PR CHECKLIST (required before merge)

```
□ No PacketEnvelope import anywhere
□ No alternate transport path introduced
□ No direct node-to-node calls
□ Handler signature is TransportPacket → TransportPacket
□ transport_hash stable across hop-only changes
□ hop_trace is append-only — no mutations
□ lineage.root_id preserved across all derived packets
□ trace_id preserved across derivation
□ tenant context not mutated across derived packets
□ schema matches models (transport-packet.schema.json in sync)
□ Tests cover changed behavior
□ No print statements
□ No forbidden log fields
□ L9_META header on all new files
□ node registration spec.yaml updated if new actions added
□ No workflow logic added to Gate or runtime nodes
```

---

## 21. ENV VAR CONTRACT

```bash
# Required at runtime
GATE_URL=               # URL of Gate service — used by GateClient
GATE_NODE_SPEC_PATH=    # path to spec.yaml — default engine/spec.yaml
GATE_ADMIN_TOKEN=       # optional — if Gate requires it for registration
L9_NODE_NAME=           # must match spec.yaml node.id

# Observability (optional — safe defaults if absent)
L9_OTEL_ENDPOINT=
L9_OTEL_METRICS_ENDPOINT=
L9_HEALTH_INTERVAL_SECONDS=
L9_REPLAY_RETENTION=
L9_AUDIT_BACKEND=
L9_AUDIT_POSTGRES_URL=
L9_GCE_URL=
L9_TRACE_SAMPLE_RATE=
L9_METRICS_ENABLED=
```

---

## 22. FINAL PRINCIPLE

```
The constellation is coherent because every node speaks one language:
TransportPacket in → domain logic → TransportPacket out → Gate → next node.

Coherence breaks the moment any node introduces:
  - a second wire format
  - a direct peer call
  - workflow state in a runtime node
  - PacketEnvelope as an active contract

There are no exceptions. There is no fallback.
```
