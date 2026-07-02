# Validation Report

## Commands executed

| Command | Result |
|---|---|
| `python -m pytest` | PASS — 4 passed |
| `python -m compileall src scripts tests` | PASS |
| `python -m py_compile scripts/export_graph_seed.py scripts/ingest_graph_seed.py scripts/sync_graph.py scripts/verify_graph.py` | PASS |
| `python -m ruff check .` | SKIPPED — ruff not installed in sandbox |

## Evidence

### pytest

```text
4 passed in 0.10s
```

### compileall

```text
Compiled src, scripts, and tests successfully.
```

### py_compile

```text
All CLI scripts compiled successfully.
```

## Notes

The sandbox Python startup emitted an unrelated `artifact_tool` spreadsheet warmup warning to stderr. The validation commands exited with status `0` except the optional ruff command, which failed only because `ruff` is not installed in the sandbox.

## Validation coverage

- Export creates node and edge records.
- Exported JSONL verifies successfully.
- Ingest writes a deterministic ingestion report.
- Sync performs export and ingest in one pass.
- Python source compiles.
- CLI scripts compile.

## Unknowns

- Live Graphiti API compatibility is Unknown because credentials, endpoint, and runtime package were not provided.
- Production V2 index shape is partially inferred from prior pack behavior; adapter accepts several common index layouts.
