#!/usr/bin/env bash
# L9-Ops-MCP one-shot install: Neo4j + deps + indices + seed + client configs
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# Export every .env assignment so child processes (pip, python, the config
# writers) see it; without set -a the values stay shell-local.
if [[ -f .env ]]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
fi

log() { printf "\n[L9] %s\n" "$*"; }

# ── 1. Neo4j ──────────────────────────────────────────────────────────────────
log "Starting Neo4j..."
docker compose -f docker-compose.neo4j.yml up -d
# Accept only the exact Docker health status "healthy" ("unhealthy" and
# "starting" are not ready).
neo4j_health() {
    local cid
    cid="$(docker compose -f docker-compose.neo4j.yml ps -q neo4j 2>/dev/null | head -n 1)"
    [[ -n "$cid" ]] || { echo "absent"; return 0; }
    docker inspect --format '{{.State.Health.Status}}' "$cid" 2>/dev/null || echo "unknown"
}
log "Waiting for Neo4j healthy (up to 90s)..."
NEO4J_HEALTH="unknown"
for _ in $(seq 1 30); do
    NEO4J_HEALTH="$(neo4j_health)"
    [[ "$NEO4J_HEALTH" = "healthy" ]] && break
    sleep 3
done
if [[ "$NEO4J_HEALTH" != "healthy" ]]; then
    echo "ERROR: Neo4j did not become healthy (last status: $NEO4J_HEALTH)" >&2
    exit 1
fi
log "Neo4j is up."

# ── 2. Python deps ────────────────────────────────────────────────────────────
log "Installing Python package + Graphiti deps..."
pip install -e ".[dev]"

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
seed_status=0
python -m l9_ops_mcp.seed || seed_status=$?
case "$seed_status" in
    0) ;;
    2) log "seed skipped (CANONICAL_LAW.md not found — set CG_ROOT)" ;;
    *) echo "ERROR: seed failed (exit $seed_status) — see output above" >&2
       exit "$seed_status" ;;
esac

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
