#!/usr/bin/env python3
from __future__ import annotations

import importlib
import sys
from validate_helpers import ROOT, status_line

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


def main() -> int:
    pyproject = ROOT / "pyproject.toml"
    if not pyproject.exists():
        print(status_line("BLOCKED", "pyproject.toml", "missing")); return 1
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    scripts = data.get("project", {}).get("scripts", {})
    failures = 0
    for name, target in sorted(scripts.items()):
        if ":" not in target:
            print(status_line("FAIL", name, f"entrypoint target lacks ':' -> {target}")); failures += 1; continue
        mod_name, attr = target.split(":", 1)
        try:
            mod = importlib.import_module(mod_name)
            obj = getattr(mod, attr)
            if not callable(obj):
                print(status_line("FAIL", name, f"{target} is not callable")); failures += 1
            else:
                print(status_line("PASS", name, f"{target} imports and is callable"))
        except Exception as exc:
            print(status_line("FAIL", name, f"cannot import {target}: {exc}")); failures += 1
    if not scripts:
        print(status_line("WARN", "pyproject.toml", "no project.scripts declared"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
