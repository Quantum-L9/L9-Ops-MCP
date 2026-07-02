"""Write or merge l9-ops-mcp into Claude Desktop MCP config. Idempotent."""
from __future__ import annotations
import json, os, pathlib, platform, sys

REPO_ROOT = pathlib.Path(__file__).parent.parent.resolve()


def _cfg_path() -> pathlib.Path:
    system = platform.system()
    if system == "Darwin":
        p = pathlib.Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        if p.parent.exists():
            return p
        return pathlib.Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    if system == "Linux":
        return pathlib.Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    print(f"Unsupported platform: {system}", file=sys.stderr)
    sys.exit(1)


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

cfg_path = _cfg_path()
cfg_path.parent.mkdir(parents=True, exist_ok=True)
cfg: dict = {}
if cfg_path.exists():
    try:
        cfg = json.loads(cfg_path.read_text())
    except json.JSONDecodeError:
        cfg = {}

cfg.setdefault("mcpServers", {})["l9-ops-mcp"] = entry
cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")
print(f"wrote: {cfg_path}")
print(f"servers: {list(cfg['mcpServers'].keys())}")
print("restart Claude Desktop to pick up config.")
