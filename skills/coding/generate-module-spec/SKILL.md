---
name: generate-module-spec
title: "generate-module-spec — L9 Module Spec Generator Skill"
purpose: "Generate a complete, production-ready Module-Spec-v2.5.yaml for any L9 module using the 6-pass workflow. Output is ready for Perplexity code generation pipeline."
summary: "Encapsulates the full L9 SuperPrompt v2.5 6-pass module spec workflow: tier classification, existing code mapping, interface extraction, orchestration flow definition, idempotency and error policy configuration, and quality gate validation. Produces one Module-Spec-v2.5.yaml per module."
version: "2.5.0"
source_files: ["IgorOS/L9-SuperPrompt-Canonical-v2.5.md"]
created: "2026-06-18"
owner: "Igor Beylin"
tags: ["module-spec", "code-generation", "l9-architecture", "fastapi", "TransportPacket", "tier-system", "R5"]
domain: "l9-engineering"
type: "skill"
ring: "R5"
production_ready: true
retrieval_keys: ["module spec", "generate module", "L9 module", "tier classification", "TransportPacket", "FastAPI module", "idempotency", "UUIDv5", "webhook adapter"]
trigger_description: "Load when generating a new L9 module spec, classifying module tier, specifying interfaces, or preparing a module for code generation."
---

# generate-module-spec

## Purpose
Generate one complete `Module-Spec-v2.5.yaml` per L9 module, ready for code generation.

## Global Constraints (Binding — Every Spec)
1. NO SUMMARIES — every fact explicit
2. NO AMBIGUITY — if it matters at runtime, it is explicit
3. NO PLACEHOLDERS — every field has real values
4. NO EXTERNAL SUPPLEMENTS — all guidance embedded
5. NO SINGLETONS — all dependencies injected
6. SSOT BINDING — these files win if they contradict this skill: DOCTRINE-Module-Spec.md, L9_RUNTIME_SSOT.md, L9_DEPENDENCIES_SSOT.md, L9_IDEMPOTENCY_SSOT.md

## Tier System

| Tier | Name | Complexity | Files | State | Examples |
|---|---|---|---|---|---|
| 1 | Simple Adapter | Low | 2-3 | Stateless | healthcheck, web.adapter |
| 2 | Integration Module | Medium | 4-7 | Threaded (UUIDv5) | slack.adapter, email.adapter, twilio.adapter |
| 3 | Complex Orchestration | High | 8+ | State machine (4+ states) | agent.executor, tool.registry, governance.engine |

## 6-Pass Workflow

### Pass 1: Classify Tier
```yaml
tier_2_if_all:
  - receives_external_webhooks OR makes_outbound_api_calls
  - integrates_with_memory_substrate
  - calls_aios_chat_endpoint
  - implements_conversation_threading_uuidv5

tier_3_if_any:
  - creates_agent_instances_dynamically
  - implements_tool_registry_dispatch
  - requires_governance_policy_evaluation
  - has_state_machine_4_plus_states

otherwise: tier_1
```

### Pass 2: Map Existing Code
- If existing: characterize behavior, gaps → REWRITE / ALIGN / WIRE decision
- If new: start from scratch

### Pass 3: Extract Interfaces
For each inbound: name, method, route, headers, payloadtype, auth
For each outbound: name, endpoint, method, timeout_seconds, retry, auth, error_handling

### Pass 4: Define Orchestration Flow
Steps must be explicit — no implicit operations.
Sections: validation → thread_id_generation → deduplication → context_reads → aios_calls → side_effects

### Pass 5: Configure Idempotency and Error Policy

Idempotency fields: enabled, mechanism, dedupe_key (primary + fallback), on_duplicate, thread_id (UUIDv5), durability

Error policy (all 5 required):
- invalid_signature: status 401, reject immediately
- stale_timestamp: status 401, reject immediately
- aios_failure: status 200, log + return ok (prevent redelivery)
- side_effect_failure: status 200, log + return ok
- storage_failure: status 200, log + continue

### Pass 6: Quality Gate Checklist
```
Pre-generation:
- module_id: lowercase snake_case
- goals: specific and measurable
- non_goals: must include "No new database tables", "No new migrations", "No parallel memory/logging/config systems"
- thread_uuid: UUIDv5 (never uuid4)
- http_client: httpx (never aiohttp or requests)
- logging: structlog (never stdlib logging or print)

Post-generation:
- acceptance tests cover every orchestration step
- all 5 error categories defined
- zero placeholder tokens
- file manifest consistent with orchestration
```

## Mandatory Standards

```yaml
identity:
  canonical_identifier: tool_id  # Always module.id, never tool_name
logging:
  library: structlog
  forbidden: [logging, print]
http_client:
  library: httpx
  forbidden: [aiohttp, requests]
thread_id:
  type: UUIDv5
  namespace: "module.l9.internal"
  never: uuid4
env_vars:
  read_at: initialization_time  # NOT import time
```

## Thread UUID Formula
```python
from uuid import uuid5, NAMESPACE_DNS
MODULE_NAMESPACE = uuid5(NAMESPACE_DNS, "module.l9.internal")
def generate_thread_uuid(source_id, channel_id, thread_ts):
    return uuid5(MODULE_NAMESPACE, f"{source_id}:{channel_id}:{thread_ts}")
```

Platform mappings:
- Slack: team_id, channel_id, ts or thread_ts
- WhatsApp: phone_number_id, from, wamid
- Email: account_id, thread_id or subject_hash, date

## Required Logging Events (All Tier 2+)
1. request_received (info): event_id, source, channel
2. signature_verified (debug): valid, method
3. thread_uuid_generated (debug): thread_uuid, components
4. dedupe_check (debug): dedupe_key, is_duplicate
5. aios_call_start (info): thread_uuid, message_preview
6. aios_call_complete (info): elapsed_ms, response_length, status
7. packet_stored (info): packet_id, packet_type, thread_uuid
8. reply_sent (info): channel, thread_ts, response_length
9. handler_error (error): error, error_type, traceback

## Output Format
One file per module: `module_{module_id}.yaml`
Use exact template from L9-SuperPrompt-Canonical-v2.5.md §MODULE_SPEC_v2.5_TEMPLATE

## Forbidden Patterns
- Creates new database tables
- Duplicates memory substrate code
- Uses module-level singletons
- Reads env vars at import time
- Uses aiohttp instead of httpx
- Uses stdlib logging instead of structlog
- Uses tool_name instead of tool_id
