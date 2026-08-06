# L9-Ops-MCP Deployment Guide

## Prerequisites
- Docker Desktop running
- Python 3.11+
- `L9_OPENAI_API_KEY` set (Graphiti entity extraction)
- Cursor IDE installed; Claude Desktop optional

## Step 1 — Environment
```bash
cp .env.example .env   # fill in L9_OPENAI_API_KEY
source .env
```

## Step 2 — One-shot bootstrap
```bash
bash scripts/install.sh
```
Does: Neo4j up → Python deps → Graphiti indices → seed CANONICAL_LAW →
Cursor mcp.json → Claude config → Governance sink patch.

## Step 3 — Preflight (all 8 gates must be green)
```bash
bash scripts/preflight.sh
```

## Step 4 — Cursor
Restart Cursor → Settings → MCP → `l9-ops-mcp` with 4 tools.

## Step 5 — Claude Desktop
```bash
source .env && python scripts/write_claude_config.py
# Restart Claude Desktop
```

## Step 6 — Tests
```bash
# Unit (no Neo4j)
pytest tests/test_budget.py tests/test_trust_ladder.py tests/test_admission.py -v

# Integration (Neo4j required)
L9_NEO4J_URI=bolt://localhost:7687 pytest tests/test_integration_graphiti.py -v
```

## Troubleshooting
| Symptom | Fix |
|---|---|
| Neo4j not healthy | `docker compose -f docker-compose.neo4j.yml logs neo4j` |
| Graphiti EntityEdge error | Pin `graphiti-core==0.3.17` |
| MCP tools missing in Cursor | Restart Cursor; verify PYTHONPATH in mcp.json |
| OpenAI key missing | Entity extraction silent-fails; set `L9_OPENAI_API_KEY` |
| All writes blocked | Callers must pass `semantic_score` > 0.65; default is 0.0 |
| Dedup blocks valid write | Adjust threshold in admission.py line `>= 0.95` |
