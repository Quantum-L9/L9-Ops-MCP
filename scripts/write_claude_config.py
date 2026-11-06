# >>> l9:meta >>>
# id: L9-Ops-MCP.script.scripts_write_claude_config__py
# title: write claude config
# artifact_type: script
# mcp_primitive: none
# callable: false
# retrievable: false
# injectable: false
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: scripts/write_claude_config.py
# content_hash: ded844fcb0e792e6bc90f9b2ff01737699b0e59b3465788e5fceaa8a319a2eb7
# token_cost_estimate: 431
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
"""Write or merge l9-ops-mcp into Claude Desktop MCP config. Idempotent."""

from __future__ import annotations
import json
import os
import pathlib
import platform
import sys

REPO_ROOT = pathlib.Path(__file__).parent.parent.resolve()


def _cfg_path() -> pathlib.Path:
    system = platform.system()
    if system == "Darwin":
        p = (
            pathlib.Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )
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
        "L9_NEO4J_URI": os.getenv("L9_NEO4J_URI", "bolt://localhost:7687"),
        "L9_NEO4J_USER": os.getenv("L9_NEO4J_USER", "neo4j"),
        "L9_NEO4J_PASS": os.getenv("L9_NEO4J_PASS", "l9_local_dev_pw"),
        "L9_OPENAI_API_KEY": os.getenv("L9_OPENAI_API_KEY", ""),
        "PYTHONPATH": str(REPO_ROOT / "src"),
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
