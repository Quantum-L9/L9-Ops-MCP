# >>> l9:meta >>>
# id: L9-Ops-MCP.script.scripts_07_l11_auto_fix_engine__py
# title: 07 L11 AUTO FIX ENGINE
# artifact_type: script
# mcp_primitive: none
# callable: false
# retrievable: false
# injectable: false
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: scripts/07-L11-AUTO-FIX-ENGINE.py
# content_hash: a5f28e5e04f5f2d3cd8845d780d905c8e03ed85cc444aaea1302f505cf2ddb5c
# token_cost_estimate: 244
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
# --- L9_META ---
# l9_schema: 1
# component: 07-L11-AUTO-FIX-ENGINE
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

"""Legacy path shim for 07-L11-AUTO-FIX-ENGINE.

Canonical implementation lives in ``scripts.l11.auto_fix_engine``.
This file preserves the historical ``scripts/07-L11-AUTO-FIX-ENGINE.py`` entrypoint used by
deploy tooling and docs; it re-exports the public API and forwards ``__main__``.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

from scripts.l11 import auto_fix_engine as _impl

# Re-export public names for ``from scripts.X import Y`` callers.
for _name in dir(_impl):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_impl, _name)
del _name

if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "l11" / "auto_fix_engine.py"
    sys.argv[0] = str(target)
    runpy.run_path(str(target), run_name="__main__")
