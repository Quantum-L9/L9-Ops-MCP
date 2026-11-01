"""OBS-12: a shebang is only honoured on line 1.

Several scripts carried ``#!/usr/bin/env python3`` after their L9_META comment
block, where the kernel ignores it. The shebang must be the first line and the
L9_META block must follow directly, and the header checks that read these
files must see the same thing with the shebang in front.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.inject_dora_complete import DoraCompleteInjector

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = sorted([*REPO_ROOT.glob("scripts/*.py"), *REPO_ROOT.glob("scripts/*.sh")])
META_OPEN = "# --- L9_META ---"
META_CLOSE = "# --- /L9_META ---"


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _has_shebang(path: Path) -> bool:
    return any(line.startswith("#!") for line in _lines(path)[:20])


SHEBANG_SCRIPTS = [p for p in SCRIPTS if _has_shebang(p)]
META_SCRIPTS = [p for p in SCRIPTS if META_OPEN in _lines(p)]


def test_inventory_is_not_empty() -> None:
    assert SHEBANG_SCRIPTS
    assert META_SCRIPTS


@pytest.mark.parametrize("path", SHEBANG_SCRIPTS, ids=lambda p: p.name)
def test_shebang_is_on_line_one(path: Path) -> None:
    lines = _lines(path)
    assert lines[0].startswith("#!"), f"{path.name}: shebang is not on line 1"
    assert not [i for i, line in enumerate(lines[1:20], 2) if line.startswith("#!")]


@pytest.mark.parametrize("path", META_SCRIPTS, ids=lambda p: p.name)
def test_l9_meta_block_leads_the_file(path: Path) -> None:
    lines = _lines(path)
    start = 1 if lines[0].startswith("#!") else 0
    assert lines[start] == META_OPEN, f"{path.name}: L9_META does not follow the shebang"
    assert META_CLOSE in lines[start:]


@pytest.mark.parametrize(
    "path", [p for p in SHEBANG_SCRIPTS if p.suffix == ".py"], ids=lambda p: p.name
)
def test_dora_header_check_unaffected_by_leading_shebang(path: Path, tmp_path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    without = tmp_path / "without" / path.name
    without.parent.mkdir()
    without.write_text(content.split("\n", 1)[1], encoding="utf-8")
    injector = DoraCompleteInjector(str(REPO_ROOT))
    assert injector.check_file(path) == injector.check_file(without)
