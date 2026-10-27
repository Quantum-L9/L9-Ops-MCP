"""RG-12 (D-05 A): the local TransportPacket builder is retired.

build_transport_packet stamped validation 'pass' for checks it never ran. The
module had no in-repository caller, so it is removed rather than kept beside
the canonical SDK envelope. This guards against its silent reintroduction.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_IMPORT = re.compile(
    r"(from\s+l9_ops_mcp(\.transport|\s+import\s+transport)\b|import\s+l9_ops_mcp\.transport\b|from\s+\.transport\b)"
)


def test_transport_module_absent() -> None:
    assert importlib.util.find_spec("l9_ops_mcp.transport") is None


def test_nothing_imports_the_retired_module() -> None:
    offenders = []
    for top in ("src", "scripts", "tests"):
        for path in (REPO_ROOT / top).rglob("*.py"):
            if path == Path(__file__).resolve():
                continue
            if _IMPORT.search(path.read_text(encoding="utf-8", errors="replace")):
                offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == []
