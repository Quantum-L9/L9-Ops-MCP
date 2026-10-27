"""Regression tests for config/policies/protected_files.yaml (decision D-11 A).

The policy is evaluated with the gate's own loader and matcher, so a path is
"protected" here exactly when scripts/validate-protected-files-v6.py would
flag it.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = REPO_ROOT / "scripts" / "validate-protected-files-v6.py"


def _load_gate() -> ModuleType:
    spec = importlib.util.spec_from_file_location("validate_protected_files_v6", GATE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def gate() -> ModuleType:
    return _load_gate()


@pytest.fixture(scope="module")
def policy(gate: ModuleType) -> dict:
    cwd = os.getcwd()
    os.chdir(REPO_ROOT)  # POLICY_PATH is repository-relative
    try:
        return gate.load_policy()
    finally:
        os.chdir(cwd)


def _protected(gate: ModuleType, policy: dict, path: str) -> bool:
    patterns = gate.get_all_protected_paths(policy) + gate.get_meta_protected_files(policy)
    return any(gate.file_matches_pattern(path, p) for p in patterns)


# D-11 A: this repository's core.
@pytest.mark.parametrize(
    "path",
    [
        "scripts/validate-protected-files-v6.py",
        "src/l9_ops_mcp/server.py",
        "src/l9_ops_mcp/kernel_registry.py",
        ".github/workflows/08-L11-CI-WORKFLOW-v3.3.yaml",
        ".github/workflows/governance.yml",
        "pyproject.toml",
        "Makefile",
        "config/policies/protected_files.yaml",
        "docker-compose.neo4j.yml",
    ],
)
def test_core_path_is_protected(gate: ModuleType, policy: dict, path: str) -> None:
    assert _protected(gate, policy, path), path


@pytest.mark.parametrize(
    "path",
    [
        "scripts/validate-protected-files-v6.py",
        "config/policies/protected_files.yaml",
        ".github/workflows/08-L11-CI-WORKFLOW-v3.3.yaml",
    ],
)
def test_gate_is_self_protected(gate: ModuleType, policy: dict, path: str) -> None:
    meta = gate.get_meta_protected_files(policy)
    assert any(gate.file_matches_pattern(path, p) for p in meta), path


def test_meta_protected_files_exist(gate: ModuleType, policy: dict) -> None:
    missing = [p for p in gate.get_meta_protected_files(policy) if not (REPO_ROOT / p).is_file()]
    assert missing == []


def test_no_foreign_layout_paths(gate: ModuleType, policy: dict) -> None:
    foreign_prefixes = ("runtime/", "core/", "memory/", ".github/scripts/")
    patterns = gate.get_all_protected_paths(policy) + gate.get_meta_protected_files(policy)
    foreign = [p for p in patterns if p.startswith(foreign_prefixes)]
    assert foreign == []


def test_unrelated_path_is_not_protected(gate: ModuleType, policy: dict) -> None:
    assert not _protected(gate, policy, "docs/README.md")
