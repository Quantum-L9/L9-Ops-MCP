#!/usr/bin/env python3
from __future__ import annotations

import ast
import re
import subprocess
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


def read_makefile_tree(makefile: Path) -> str:
    """Read literal, contained includes without executing repository Make code."""
    root = makefile.resolve().parent
    active: set[Path] = set()

    def visit(source: Path) -> str:
        resolved = source.resolve()
        if not resolved.is_relative_to(root):
            raise ValueError(f"Make include escapes repository: {source}")
        if resolved in active:
            raise ValueError(f"Cyclic Make include: {source}")
        if not source.is_file():
            raise ValueError(f"Required Make include missing: {source}")
        active.add(resolved)
        fragments = [source.read_text(encoding="utf-8")]
        for raw in fragments[0].splitlines():
            if raw.startswith("\t"):
                continue
            match = re.match(r"^\s*(-?include|sinclude)\s+([^#]+)", raw)
            if not match:
                continue
            for name in match.group(2).split():
                if any(char in name for char in "$*?[]\\"):
                    raise ValueError(f"Non-literal Make include is not auditable: {name}")
                included = root / name
                if match.group(1) != "include" and not included.exists():
                    continue
                fragments.append(visit(included))
        active.remove(resolved)
        return "\n".join(fragments)

    return visit(makefile)


def extract_make_targets(makefile: str) -> set[str]:
    targets: set[str] = set()
    for line in makefile.splitlines():
        if line.startswith("\t") or not line or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+(?:\s+[A-Za-z0-9_.-]+)*):(?!=)", line)
        if match:
            targets.update(match.group(1).split())
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
