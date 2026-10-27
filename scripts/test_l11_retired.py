# --- L9_META ---
# l9_schema: 1
# component: test_l11_retired
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

"""Regression tests for retired L11 surfaces (decisions D-08 A, D-09 A).

DORA:
    component_id: test-l11-retired
    tier: 3
    lifecycle: production
    owner: platform-engineering
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_CONFIG = REPO_ROOT / "scripts" / "l11" / "pipeline_config.yaml"


def _python_sources() -> list[Path]:
    """Tracked-tree Python sources under scripts/ and tests/ (not this file)."""
    roots = [REPO_ROOT / "scripts", REPO_ROOT / "tests"]
    this = Path(__file__).resolve()
    return [p for root in roots for p in root.rglob("*.py") if p.resolve() != this]


def _referencing(pattern: str) -> list[str]:
    rx = re.compile(pattern)
    return sorted(
        str(p.relative_to(REPO_ROOT))
        for p in _python_sources()
        if rx.search(p.read_text(encoding="utf-8", errors="replace"))
    )


class TestAutoFixRetired:
    """RG-30 (D-08 A): the destructive auto-fix engine is absent."""

    def test_engine_module_and_shim_are_gone(self):
        assert importlib.util.find_spec("scripts.l11.auto_fix_engine") is None
        assert not (REPO_ROOT / "scripts" / "07-L11-AUTO-FIX-ENGINE.py").exists()

    def test_no_python_source_references_auto_fix_engine(self):
        assert _referencing(r"AutoFixEngine|auto_fix_engine") == []

    def test_pipeline_config_has_no_auto_fix_block(self):
        cfg = yaml.safe_load(PIPELINE_CONFIG.read_text())
        assert "auto_fix" not in cfg.get("remediation", {})
