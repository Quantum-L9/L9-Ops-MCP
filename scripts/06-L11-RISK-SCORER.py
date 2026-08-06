# --- L9_META ---
# l9_schema: 1
# component: 06-L11-RISK-SCORER
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

"""Legacy path shim for 06-L11-RISK-SCORER.

Canonical implementation lives in ``scripts.l11.risk_scorer``.
This file preserves the historical ``scripts/06-L11-RISK-SCORER.py`` entrypoint used by
deploy tooling and docs; it re-exports the public API and forwards ``__main__``.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

from scripts.l11 import risk_scorer as _impl

# Re-export public names for ``from scripts.X import Y`` callers.
for _name in dir(_impl):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_impl, _name)
del _name

if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "l11" / "risk_scorer.py"
    sys.argv[0] = str(target)
    runpy.run_path(str(target), run_name="__main__")
