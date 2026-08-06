# Graph Export Adapter

## Purpose

Exports V2 metadata/retrieval indexes into `graph-seed.jsonl`.

## Input

A JSON index containing artifact objects. Supported top-level layouts:

- list of objects
- `{ "artifacts": [...] }`
- `{ "items": [...] }`
- `{ "records": [...] }`
- `{ "documents": [...] }`
- `{ "resources": [...] }`

## Output

JSONL records:

- `artifact_node`
- `artifact_edge`

## Mapping

| V2 field | Graph field |
|---|---|
| `id` / `artifact_id` | `artifact.id` |
| `artifact_type` / `type` | `artifact.artifact_type` |
| `source_path` / `path` / `file` | `artifact.source_path` |
| `retrieval_keys` / `activation_signals` / `tags` | `artifact.activation_signals` |
| `dependencies` / `depends_on` / `requires` | dependency edges |

## Failure behavior

The adapter fails closed for missing required node fields, invalid JSON, unsupported records, and malformed callable metadata.
