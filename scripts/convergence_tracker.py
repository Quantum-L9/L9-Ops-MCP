#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from validate_helpers import ROOT, status_line

SCAN = ["README.md", "AGENTS.md", "Makefile", "docs", "skills", "playbooks", "scripts", "schemas"]


def main() -> int:
    unknowns = []
    todos = []
    for item in SCAN:
        path = ROOT / item
        if not path.exists():
            unknowns.append(item)
            continue
        files = [path] if path.is_file() else [p for p in path.rglob("*") if p.is_file()]
        for f in files:
            if f.suffix.lower() not in {".md", ".yaml", ".yml", ".json", ".py", ".sh", ".toml"}:
                continue
            text = f.read_text(encoding="utf-8", errors="ignore")
            for m in re.finditer(r"\b(TODO|PLACEHOLDER|STUB|UNKNOWN)\b", text):
                todos.append({"file": str(f.relative_to(ROOT)), "marker": m.group(1)})
    status = "converged" if not unknowns and not todos else "partial"
    print(json.dumps({"convergence_status": status, "missing_paths": unknowns, "markers": todos[:100]}, indent=2))
    print(status_line("PASS" if status == "converged" else "WARN", "convergence", status))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
