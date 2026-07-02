#!/usr/bin/env python3
from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def status_line(status: str, check: str, detail: str) -> str:
    return f"{status}: {check}: {detail}"


def find_markdown_links(text: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text)]


def extract_make_targets(makefile: str) -> set[str]:
    targets: set[str] = set()
    for line in makefile.splitlines():
        if line.startswith("\t") or not line or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+):", line)
        if match:
            targets.add(match.group(1))
    return targets


def extract_readme_make_commands(text: str) -> set[str]:
    return set(re.findall(r"\bmake\s+([A-Za-z0-9_.-]+)", text))


def python_syntax_ok(path: Path) -> tuple[bool, str]:
    try:
        ast.parse(read(path), filename=str(path))
        return True, "syntax ok"
    except SyntaxError as exc:
        return False, f"line {exc.lineno}: {exc.msg}"


def run_command(cmd: list[str], cwd: Path = ROOT, timeout: int = 30) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, timeout=timeout)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def iter_files(*roots: str, suffixes: tuple[str, ...] | None = None) -> Iterable[Path]:
    for root in roots:
        base = ROOT / root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and (suffixes is None or path.suffix in suffixes):
                yield path
