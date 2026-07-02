#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from validate_helpers import ROOT, status_line

CATEGORIES = {
    "skills": "skills/",
    "playbooks": "playbooks/",
    "schemas": "schemas/",
    "scripts": "scripts/",
    "runtime": "src/l9_ops_mcp/",
    "workflows": ".github/workflows/",
    "docs": "docs/",
}


def changed_files() -> list[str]:
    try:
        proc = subprocess.run(["git", "diff", "--name-only", "origin/main...HEAD"], cwd=ROOT, text=True, capture_output=True, check=False)
        files = [x for x in proc.stdout.splitlines() if x]
        return files
    except Exception:
        return []


def classify(files: list[str]) -> dict[str, list[str]]:
    out = {k: [] for k in CATEGORIES}
    out["other"] = []
    for f in files:
        hit = False
        for name, prefix in CATEGORIES.items():
            if f.startswith(prefix):
                out[name].append(f); hit = True
        if not hit:
            out["other"].append(f)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    files = changed_files()
    if not files:
        files = [str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]
    matrix = classify(files)
    print(json.dumps({"changed_or_scanned_count": len(files), "impact": matrix}, indent=2))
    for area, items in matrix.items():
        if items:
            print(status_line("PASS", "impact", f"{area}: {len(items)} file(s)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
