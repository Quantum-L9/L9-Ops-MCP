# >>> l9:meta >>>
# id: L9-Ops-MCP.script.scripts_04_l11_ai_enrichment_engine__py
# title: 04 L11 AI ENRICHMENT ENGINE
# artifact_type: script
# mcp_primitive: none
# callable: false
# retrievable: false
# injectable: false
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: scripts/04-L11-AI-ENRICHMENT-ENGINE.py
# content_hash: ce4d8fe307f59ff9220e7b0099729b628881062f1833923c7d11ad262a3ed767
# token_cost_estimate: 251
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
# --- L9_META ---
# l9_schema: 1
# component: 04-L11-AI-ENRICHMENT-ENGINE
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

"""Legacy path shim for 04-L11-AI-ENRICHMENT-ENGINE.

Canonical implementation lives in ``scripts.l11.ai_enrichment_engine``.
This file preserves the historical ``scripts/04-L11-AI-ENRICHMENT-ENGINE.py`` entrypoint used by
deploy tooling and docs; it re-exports the public API and forwards ``__main__``.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

from scripts.l11 import ai_enrichment_engine as _impl

# Re-export public names for ``from scripts.X import Y`` callers.
for _name in dir(_impl):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_impl, _name)
del _name

if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "l11" / "ai_enrichment_engine.py"
    sys.argv[0] = str(target)
    runpy.run_path(str(target), run_name="__main__")
