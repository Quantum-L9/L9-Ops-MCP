---
l9_schema: 1
artifact_type: documentation
tags: ['docs', 'retrieval', 'skill']
retrieval: on_demand
status: active
---
# SKILL: agents.project-memory
## Version: 1.0.0
## Source: vasilyu1983/AI-Agents-public#agents-project-memory/SKILL.md (adapted for L9 kernel continuity)

## Purpose
Durable memory layer for the L9 portable_agent_runtime. Provides read/write/search
operations on the kernel continuity store. All writes are append-logged.
All reads return provenance (when written, by which run_id).

## Memory Namespaces
- `session:<session_id>` — per-session context (TTL: 7 days)
- `agent:<agent_id>` — agent-scoped durable facts (TTL: 90 days)
- `playbook:<playbook_id>` — playbook execution history summaries (TTL: 1 year)
- `global:conventions` — L9 naming conventions, glossary, style rules (no TTL)
- `global:decisions` — Durable architectural decisions (no TTL)

## Write Contract
```json
{
  "namespace": "<namespace>",
  "key": "<string>",
  "value": "<any>",
  "run_id": "<string>",
  "ttl_seconds": "<integer|null>",
  "schema_version": "1.0"
}
```

## Read Contract
```json
{
  "namespace": "<namespace>",
  "key": "<string>",
  "result": "<any|null>",
  "written_at": "<ISO8601>",
  "written_by_run_id": "<string>",
  "schema_version": "1.0"
}
```

## Behavior Rules
- Never overwrite a `global:decisions` entry — append a new versioned entry instead.
- All session memory writes are idempotent (last-write-wins within a run).
- Memory reads that miss the store return `null` (never throw).
- Memory is NOT in LLM context by default — it must be explicitly loaded per task.
