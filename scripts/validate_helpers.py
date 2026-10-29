#!/usr/bin/env python3
from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable

import yaml

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
    return [m.group(1) for m in re.finditer(r"\[[^\[\]]+\]\(([^)]+)\)", text)]


_RULE = re.compile(r"^([A-Za-z0-9_.%/ -]+?)\s*::?(?![=:])")
_SPECIAL_TARGET = re.compile(r"^\.[A-Z_]+$")


def extract_make_targets(makefile: str) -> set[str]:
    """Return rule targets; variable assignments and special targets are not targets."""
    targets: set[str] = set()
    for line in makefile.splitlines():
        if line.startswith("\t") or not line or line.lstrip().startswith("#"):
            continue
        if re.match(r"^[A-Za-z0-9_.-]+\s*(?::=|::=|\?=|\+=|!=|=)", line):
            continue
        match = _RULE.match(line)
        if not match:
            continue
        for name in match.group(1).split():
            if not _SPECIAL_TARGET.match(name):
                targets.add(name)
    return targets


# ``make <target>`` only where ``make`` is in command position: start of a
# (possibly indented, bulleted or prompted) line, a workflow ``run:`` value,
# after ``&&`` / ``||``, or the start of an inline code span.  Prose such as
# "make sure ..." mid-sentence is not a command reference.
_MAKE_COMMAND = re.compile(
    r"(?:(?:^[ \t]*(?:[-*]\s+)?(?:\$\s+|run:\s*)?)|(?:(?:&&|\|\|)\s*)|`)make\s+([A-Za-z0-9_.-]+)",
    re.MULTILINE,
)


def extract_readme_make_commands(text: str) -> set[str]:
    return {name for name in _MAKE_COMMAND.findall(text) if not name.startswith("-")}


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


def resolve_repo_path(value: str | Path) -> Path:
    """Resolve a validator input path; relative paths are anchored at the repository root."""
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


class MetadataError(ValueError):
    """Raised when a file's metadata block exists but cannot be parsed."""


_FRONTMATTER_FENCE = "---"
_HTML_META_OPEN = re.compile(r"^<!--\s*L9_META\s*$")
_HTML_META_CLOSE = re.compile(r"^/L9_META\s*-->\s*$")


def parse_frontmatter(text: str) -> Any:
    """Return the parsed leading metadata block of ``text``.

    Recognises a ``---`` fenced YAML frontmatter block (fences on their own
    lines) and the ``<!-- L9_META ... /L9_META -->`` block used by kernel
    markdown.  Returns ``None`` when there is no leading block; raises
    :class:`MetadataError` when the block is unterminated or invalid YAML.
    """
    lines = text.splitlines()
    if not lines:
        return None
    if lines[0].strip() == _FRONTMATTER_FENCE:
        closer = re.compile(r"^---$")
    elif _HTML_META_OPEN.match(lines[0].strip()):
        closer = _HTML_META_CLOSE
    else:
        return None
    for index in range(1, len(lines)):
        if closer.match(lines[index].strip()):
            block = "\n".join(lines[1:index])
            try:
                return yaml.safe_load(block)
            except yaml.YAMLError as exc:
                raise MetadataError(f"invalid YAML metadata block: {exc}") from exc
    raise MetadataError("unterminated metadata block")


def load_metadata(path: Path) -> Any:
    """Parse a file's metadata structurally.

    Markdown: the leading frontmatter / L9_META block (``None`` when absent).
    YAML: a leading frontmatter block merged with the first mapping document
    after it, otherwise the whole document.  Raises :class:`MetadataError` on
    invalid YAML.
    """
    text = path.read_text(encoding="utf-8")
    front = parse_frontmatter(text)
    if path.suffix not in {".yaml", ".yml"}:
        return front
    try:
        documents = [doc for doc in yaml.safe_load_all(text) if doc is not None]
    except yaml.YAMLError as exc:
        raise MetadataError(f"invalid YAML: {exc}") from exc
    if not documents:
        return None
    merged: dict[str, Any] = {}
    mappings = [doc for doc in documents if isinstance(doc, dict)]
    if not mappings:
        return documents[0]
    for doc in mappings:
        merged.update(doc)
    return merged


def missing_fields(meta: Any, required: Iterable[str]) -> list[str]:
    """Required keys that are absent, null or empty in a metadata mapping."""
    if not isinstance(meta, dict):
        return list(required)
    return [field for field in required if meta.get(field) in (None, "", [], {})]
