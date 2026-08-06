#!/usr/bin/env bash
# L9-Ops-MCP preflight — 8 gates, exits 0=green 1=blocking failure
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
[ -f .env ] && source .env || true

PASS=0; FAIL=0

check() {
    local label="$1"; shift
    if "$@" &>/dev/null; then
        printf "  ✅  %s\n" "$label"; ((PASS++)) || true
    else
        printf "  ❌  %s\n" "$label"; ((FAIL++)) || true
    fi
}

echo ""
echo "══════════════════════════════════════════════"
echo " L9-Ops-MCP PREFLIGHT  $(date +%Y-%m-%dT%H:%M:%S)"
echo "══════════════════════════════════════════════"

# ── 1. Dependencies ───────────────────────────────────────────────────────────
echo ""; echo "── 1. Dependencies ───────────────────────────"
check "Python >=3.11"           python -c "import sys; assert sys.version_info>=(3,11)"
check "graphiti-core installed" python -c "import graphiti_core"
check "mcp installed"           python -c "import mcp"
check "neo4j driver installed"  python -c "import neo4j"
check "tiktoken installed"      python -c "import tiktoken"
check "l9_ops_mcp installed"    python -c "import l9_ops_mcp"

# ── 2. Neo4j connectivity ─────────────────────────────────────────────────────
echo ""; echo "── 2. Neo4j connectivity ─────────────────────"
check "Neo4j bolt reachable" python - <<'PY'
from neo4j import GraphDatabase
import os
d = GraphDatabase.driver(
    os.getenv("L9_NEO4J_URI",  "bolt://localhost:7687"),
    auth=(os.getenv("L9_NEO4J_USER", "neo4j"),
          os.getenv("L9_NEO4J_PASS", "l9_local_dev_pw")),
)
d.verify_connectivity()
d.close()
PY

# ── 3. Graphiti smoke ─────────────────────────────────────────────────────────
echo ""; echo "── 3. Graphiti smoke ─────────────────────────"
check "Graphiti indices build" python - <<'PY'
import asyncio
from l9_ops_mcp.graphiti_client import get_graphiti
asyncio.run(get_graphiti())
PY

check "Graphiti episode ingest" python - <<'PY'
import asyncio
from datetime import datetime, timezone
from l9_ops_mcp.graphiti_client import get_graphiti
async def t():
    g = await get_graphiti()
    await g.add_episode(
        name="preflight-test",
        episode_body="preflight smoke test for L9",
        source_description="preflight.sh",
        group_id="session:preflight",
        reference_time=datetime.now(timezone.utc),
    )
asyncio.run(t())
PY

check "Graphiti search returns results" python - <<'PY'
import asyncio
from l9_ops_mcp.graphiti_client import get_graphiti
async def t():
    g = await get_graphiti()
    r = await g.search("preflight smoke test", num_results=1)
    assert r, "search returned empty"
asyncio.run(t())
PY

# ── 4. Hydrator ───────────────────────────────────────────────────────────────
echo ""; echo "── 4. Hydrator ───────────────────────────────"
check "Hydrator returns read-only payload" python - <<'PY'
import asyncio
from l9_ops_mcp.hydrator import hydrate
async def t():
    p = await hydrate("preflight", "preflight-agent", 4000, "L2", "s-preflight")
    assert p.readonly is True
    assert 0 <= p.budget_remaining_tokens <= 4000
asyncio.run(t())
PY

# ── 5. Admission gate ─────────────────────────────────────────────────────────
echo ""; echo "── 5. Admission gate ─────────────────────────"
check "Low-score candidate quarantined" python - <<'PY'
import asyncio
from l9_ops_mcp.admission import evaluate
from l9_ops_mcp.models import MemoryCandidate

async def no_dup(_body: str) -> bool:
    return False

async def t():
    c = MemoryCandidate(
        body="noise",
        source_agent_id="preflight-agent",
        session_id="s-preflight",
        semantic_score=0.1,
    )
    ok, disposition = await evaluate(c, no_dup)
    assert not ok, f"expected quarantine, got admitted (disposition={disposition})"

asyncio.run(t())
PY

check "Valid candidate admitted" python - <<'PY'
import asyncio
from l9_ops_mcp.admission import evaluate
from l9_ops_mcp.models import MemoryCandidate

async def no_dup(_body: str) -> bool:
    return False

async def t():
    c = MemoryCandidate(
        body="L9 preflight: valid architectural decision",
        source_agent_id="preflight-agent",
        session_id="s-preflight",
        semantic_score=0.95,
        trust_level="L2",
    )
    ok, disposition = await evaluate(c, no_dup)
    assert ok, f"expected admit, got {disposition}"

asyncio.run(t())
PY

# ── 6. MCP tool surface ───────────────────────────────────────────────────────
echo ""; echo "── 6. MCP tool surface ───────────────────────"
check "MCP server importable"  python -c "from l9_ops_mcp.server import mcp"
check "Required tools registered" python - <<'PY'
from l9_ops_mcp.server import mcp
tools = {t.name for t in mcp._tool_manager.list_tools()}
required = {"memory_get_budget_slice", "memory_ingest_episode",
            "memory_query_context", "memory_invalidate_fact"}
missing = required - tools
assert not missing, f"missing tools: {missing}"
PY

# ── 7. Cursor MCP config ──────────────────────────────────────────────────────
echo ""; echo "── 7. Cursor MCP config ──────────────────────"
CURSOR_CFG="$HOME/.cursor/mcp.json"
check "~/.cursor/mcp.json exists" test -f "$CURSOR_CFG"
check "l9-ops-mcp entry present" python - <<PY
import json, pathlib
cfg = json.loads(pathlib.Path("$CURSOR_CFG").read_text())
assert "l9-ops-mcp" in cfg.get("mcpServers", {}), "l9-ops-mcp key missing"
PY

# ── 8. Cursor-Governance sink ─────────────────────────────────────────────────
echo ""; echo "── 8. Cursor-Governance sink ─────────────────"
CG_SINK="${CG_ROOT:-$HOME/.cursor-governance}/intelligence/context-memory/graphiti_sink.py"
check "graphiti_sink.py present" test -f "$CG_SINK"

echo ""
echo "══════════════════════════════════════════════"
printf " RESULT: %d passed  %d failed\n" "$PASS" "$FAIL"
echo "══════════════════════════════════════════════"
echo ""
[ "$FAIL" -eq 0 ] || exit 1
