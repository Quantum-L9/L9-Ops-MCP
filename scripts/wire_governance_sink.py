"""Patch Cursor-Governance context-extractor.py to emit Graphiti episodes.

Idempotent: skips if already patched. Creates .pre-graphiti.bak backup.
Set CG_ROOT env var if Cursor-Governance lives outside ~/.cursor-governance.
"""
from __future__ import annotations

import os
import pathlib
import re
import shutil

CG_ROOT   = pathlib.Path(os.getenv("CG_ROOT", str(pathlib.Path.home() / ".cursor-governance")))
EXTRACTOR = CG_ROOT / "intelligence" / "context-memory" / "context-extractor.py"
SINK_SRC  = (
    pathlib.Path(__file__).parent.parent
    / "Cursor-Governance"
    / "intelligence"
    / "context-memory"
    / "graphiti_sink.py"
)
MARKER = "# L9-GRAPHITI-SINK-PATCHED"

_INJECT = """

# ── L9 Graphiti sink (injected by wire_governance_sink.py) ──
# L9-GRAPHITI-SINK-PATCHED
try:
    from graphiti_sink import emit_session as _emit_graphiti
    _graphiti_available = True
except ImportError:
    _graphiti_available = False


def _save_and_emit(session_data: dict) -> None:
    \"Save JSON cache AND emit Graphiti episode.\"
    save_to_sessions_dir(session_data)
    if _graphiti_available:
        try:
            _emit_graphiti(session_data)
        except Exception as _e:
            import sys
            print(f"[graphiti_sink] warn: {_e}", file=sys.stderr)
# ── end L9 Graphiti sink ──
"""


def main() -> None:
    if not EXTRACTOR.exists():
        print(f"skip: {EXTRACTOR} not found  (set CG_ROOT env var)")
        return

    src = EXTRACTOR.read_text(encoding="utf-8")

    if MARKER in src:
        print("skip: context-extractor.py already patched")
        return

    bak = EXTRACTOR.with_suffix(".py.pre-graphiti.bak")
    shutil.copy(EXTRACTOR, bak)
    print(f"backup: {bak}")

    if SINK_SRC.exists():
        shutil.copy(SINK_SRC, EXTRACTOR.parent / "graphiti_sink.py")
        print("installed: graphiti_sink.py")

    patched, n = re.subn(
        r"\bsave_to_sessions_dir\(session_data\)",
        _INJECT.strip() + "\n    _save_and_emit(session_data)",
        src,
        count=1,
    )
    if n == 0:
        patched = src + _INJECT
        patched += "# NOTE: manually wire _save_and_emit() into your save call\n"

    EXTRACTOR.write_text(patched, encoding="utf-8")
    print(f"patched: {EXTRACTOR}")


if __name__ == "__main__":
    main()
