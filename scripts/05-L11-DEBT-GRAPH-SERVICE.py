# >>> l9:meta >>>
# id: L9-Ops-MCP.script.scripts_05_l11_debt_graph_service__py
# title: 05 L11 DEBT GRAPH SERVICE
# artifact_type: script
# mcp_primitive: none
# callable: false
# retrievable: false
# injectable: false
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: scripts/05-L11-DEBT-GRAPH-SERVICE.py
# content_hash: 376a21bf88f8cf19010b23e7c75e4f5b5f0a8e72b3df9522f34a1f6bec34e644
# token_cost_estimate: 248
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
# --- L9_META ---
# l9_schema: 1
# component: 05-L11-DEBT-GRAPH-SERVICE
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

"""Legacy path shim for 05-L11-DEBT-GRAPH-SERVICE.

Canonical implementation lives in ``scripts.l11.debt_graph_service``.
This file preserves the historical ``scripts/05-L11-DEBT-GRAPH-SERVICE.py`` entrypoint used by
deploy tooling and docs; it re-exports the public API and forwards ``__main__``.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

from scripts.l11 import debt_graph_service as _impl

# Re-export public names for ``from scripts.X import Y`` callers.
for _name in dir(_impl):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_impl, _name)
del _name

if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "l11" / "debt_graph_service.py"
    sys.argv[0] = str(target)
    runpy.run_path(str(target), run_name="__main__")
