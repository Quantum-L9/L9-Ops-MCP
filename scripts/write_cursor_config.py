"""Write or merge l9-ops-mcp entry into ~/.cursor/mcp.json. Idempotent.

The existing config is never discarded: if it is not plain JSON (e.g. JSONC
with comments) or does not have the expected shape, the file is left untouched
and the script exits 1 naming the file and the reason. The file carries
credentials, so it is written atomically with mode 0600.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile
from typing import Any

CURSOR_DIR = pathlib.Path.home() / ".cursor"
MCP_JSON = CURSOR_DIR / "mcp.json"
REPO_ROOT = pathlib.Path(__file__).parent.parent.resolve()
SERVER_NAME = "l9-ops-mcp"


class ConfigRefusal(Exception):
    """The existing config cannot be merged safely; it is left untouched."""


def build_entry() -> dict[str, Any]:
    return {
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


def load_config(path: pathlib.Path) -> dict[str, Any]:
    """Return the existing config, or {} when absent. Refuse anything unusable."""
    if not path.exists():
        return {}
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        msg = f"{path} is not readable plain JSON ({exc})"
        raise ConfigRefusal(msg) from exc
    if not isinstance(cfg, dict):
        msg = f"{path} top level is {type(cfg).__name__}, expected a JSON object"
        raise ConfigRefusal(msg)
    servers = cfg.get("mcpServers", {})
    if not isinstance(servers, dict):
        msg = f'{path} "mcpServers" is {type(servers).__name__}, expected a JSON object'
        raise ConfigRefusal(msg)
    return cfg


def write_private_atomic(path: pathlib.Path, text: str) -> None:
    """Replace ``path`` atomically with ``text``, readable by the owner only."""
    target = path.resolve() if path.is_symlink() else path
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, target)
    except BaseException:
        pathlib.Path(tmp_name).unlink(missing_ok=True)
        raise


def merge_entry(path: pathlib.Path, entry: dict[str, Any]) -> dict[str, Any]:
    cfg = load_config(path)
    cfg.setdefault("mcpServers", {})[SERVER_NAME] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    write_private_atomic(path, json.dumps(cfg, indent=2) + "\n")
    return cfg


def main() -> int:
    try:
        cfg = merge_entry(MCP_JSON, build_entry())
    except ConfigRefusal as exc:
        print(f"refusing to modify {MCP_JSON}: {exc}", file=sys.stderr)
        print(
            f'add the "{SERVER_NAME}" entry under "mcpServers" manually, or fix the file '
            "and re-run this script.",
            file=sys.stderr,
        )
        return 1
    print(f"wrote: {MCP_JSON}")
    print(f"servers: {list(cfg['mcpServers'].keys())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
