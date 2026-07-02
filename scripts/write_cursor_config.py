"""Write or merge l9-ops-mcp entry into ~/.cursor/mcp.json. Idempotent."""
from __future__ import annotations
import json, os, pathlib

CURSOR_DIR = pathlib.Path.home() / ".cursor"
MCP_JSON   = CURSOR_DIR / "mcp.json"
REPO_ROOT  = pathlib.Path(__file__).parent.parent.resolve()

entry = {
    "command": "python",
    "args": ["-m", "l9_ops_mcp.server"],
    "env": {
        "L9_NEO4J_URI":      os.getenv("L9_NEO4J_URI",  "bolt://localhost:7687"),
        "L9_NEO4J_USER":     os.getenv("L9_NEO4J_USER", "neo4j"),
        "L9_NEO4J_PASS":     os.getenv("L9_NEO4J_PASS", "l9_local_dev_pw"),
        "L9_OPENAI_API_KEY": os.getenv("L9_OPENAI_API_KEY", ""),
        "PYTHONPATH":        str(REPO_ROOT / "src"),
    },
}

CURSOR_DIR.mkdir(parents=True, exist_ok=True)
cfg: dict = {}
if MCP_JSON.exists():
    try:
        cfg = json.loads(MCP_JSON.read_text())
    except json.JSONDecodeError:
        cfg = {}

cfg.setdefault("mcpServers", {})["l9-ops-mcp"] = entry
MCP_JSON.write_text(json.dumps(cfg, indent=2) + "\n")
print(f"wrote: {MCP_JSON}")
print(f"servers: {list(cfg['mcpServers'].keys())}")
