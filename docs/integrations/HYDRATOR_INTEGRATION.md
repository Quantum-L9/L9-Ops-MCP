# Hydrator Integration

## Role

The hydrator uses graph memory to select artifact pointers and then retrieves canonical artifact bodies from the repo/RAG layer.

## Query strategy

1. Query graph for matching activation signals, artifact types, dependencies, and prior decisions.
2. Resolve graph nodes to canonical `source_path`.
3. Retrieve the full artifact body from repo/RAG.
4. Apply context budget and authority rules.
5. Emit `RuntimePayload`.

## Anti-drift rule

The graph may store summaries and relationships, but canonical instructions remain in the repo.

## RuntimePayload fields

Recommended fields:

- `selected_artifacts`
- `artifact_sources`
- `graph_evidence`
- `context_budget`
- `authority_rules`
- `unknowns`
- `trace_id`
