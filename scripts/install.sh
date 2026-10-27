#!/usr/bin/env bash
# L9-Ops-MCP one-shot install: Neo4j + deps + indices + seed + client configs
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
[ -f .env ] && source .env || true

log() { printf "\n[L9] %s\n" "$*"; }

# ── 1. Neo4j ──────────────────────────────────────────────────────────────────
log "Starting Neo4j..."
docker compose -f docker-compose.neo4j.yml up -d
log "Waiting for Neo4j healthy (up to 90s)..."
for i in $(seq 1 30); do
    docker compose -f docker-compose.neo4j.yml ps | grep -q "healthy" && break
    sleep 3
done
docker compose -f docker-compose.neo4j.yml ps | grep -q "healthy" \
    || { echo "ERROR: Neo4j did not become healthy"; exit 1; }
log "Neo4j is up."

# ── 2. Python deps ────────────────────────────────────────────────────────────
log "Installing Python package + Graphiti deps..."
pip install -e ".[dev]" \
    "graphiti-core>=0.3.17" \
    "neo4j>=5.20.0" \
    "mcp[cli]>=1.2.0" \
    "tiktoken>=0.7.0" \
    "httpx>=0.27.0"

# ── 3. Graphiti indices ───────────────────────────────────────────────────────
log "Building Graphiti indices & constraints..."
python - <<'PY'
import asyncio
from l9_ops_mcp.graphiti_client import get_graphiti
asyncio.run(get_graphiti())
print("  indices: ok")
PY

# ── 4. Seed global:decisions ──────────────────────────────────────────────────
log "Seeding global:decisions from CANONICAL_LAW.md..."
python -m l9_ops_mcp.seed || log "seed skipped (CANONICAL_LAW.md not found — set CG_ROOT)"

# ── 5. Cursor MCP config ──────────────────────────────────────────────────────
# The writers refuse (exit 1, reason on stderr) rather than overwrite a config
# they cannot parse; install continues so the user can merge the entry by hand.
log "Writing ~/.cursor/mcp.json..."
if python scripts/write_cursor_config.py; then
    log "Cursor MCP config written."
else
    log "Cursor MCP config NOT written (see message above); add the l9-ops-mcp entry manually."
fi

# ── 6. Claude Desktop config (optional) ──────────────────────────────────────
if python scripts/write_claude_config.py; then
    log "Claude Desktop config written."
else
    log "Claude Desktop config NOT written (see message above)."
fi

log "Install complete. Run: bash scripts/preflight.sh"
