"""OBS-02: the L11 workflow's ``pull_request.paths`` filter must reach every
protected path, otherwise a PR touching only a protected file (``Makefile``,
``.pre-commit-config.yaml``, ...) never runs the protected-files gate.

Matching follows GitHub's filter-pattern cheat sheet: ``*`` matches any run of
characters except ``/``, ``**`` matches any run including ``/``, ``?`` matches
one character. Each protected pattern is instantiated into concrete sample
paths, and every sample must be matched by some ``paths`` entry.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "08-L11-CI-WORKFLOW-v3.3.yaml"
POLICY = REPO_ROOT / "config" / "policies" / "protected_files.yaml"
GATE_PATH = REPO_ROOT / "scripts" / "validate-protected-files-v6.py"


def _load_gate() -> ModuleType:
    spec = importlib.util.spec_from_file_location("validate_protected_files_v6", GATE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()


def _github_glob_to_regex(pattern: str) -> re.Pattern[str]:
    out: list[str] = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def _samples(protected: str) -> list[str]:
    """Concrete paths a protected pattern stands for."""
    variants = [("pkg/sub/mod.py", "x"), ("mod.py", "")]
    samples: list[str] = []
    for deep, star in variants:
        sample = protected.replace("**", "\0").replace("*", star).replace("?", "x")
        sample = sample.replace("\0", deep)
        if sample and not sample.endswith("/"):
            samples.append(sample)
    return samples


def _pr_paths() -> list[str]:
    workflow: dict[Any, Any] = yaml.safe_load(WORKFLOW.read_text())
    # PyYAML (YAML 1.1) parses the bare key ``on`` as boolean True.
    triggers = workflow.get("on", workflow.get(True))
    paths = triggers["pull_request"]["paths"]
    assert isinstance(paths, list) and paths
    return [str(p) for p in paths]


def _protected_patterns(policy: dict[str, Any] | None = None) -> list[str]:
    """Every pattern the gate protects, derived with the gate's own accessors
    (F-pr38-15: a second derivation read subsystem 'paths' while the gate reads
    'protected_paths'), plus .pre-commit-config.yaml, which this filter must
    also reach."""
    if policy is None:
        policy = yaml.safe_load(POLICY.read_text())
    patterns = GATE.get_all_protected_paths(policy) + GATE.get_meta_protected_files(policy)
    patterns.append(".pre-commit-config.yaml")
    return sorted(set(patterns))


def test_patterns_include_subsystem_protected_paths() -> None:
    policy = {
        "categories": {
            "lcto_controlled": {"protected_paths": ["Makefile"]},
            "subsystem_protected": {
                "subsystems": {"engine": {"protected_paths": ["engine/core/**"]}}
            },
        },
        "meta_protected_files": ["config/policies/protected_files.yaml"],
    }
    assert "engine/core/**" in _protected_patterns(policy)
    assert set(_protected_patterns(policy)) == {
        "Makefile",
        "engine/core/**",
        "config/policies/protected_files.yaml",
        ".pre-commit-config.yaml",
    }


def test_glob_semantics_match_github() -> None:
    assert _github_glob_to_regex("src/**").match("src/a/b/c.py")
    assert not _github_glob_to_regex("*.toml").match("dir/x.toml")
    assert _github_glob_to_regex("docker-compose*.yml").match("docker-compose.yml")


@pytest.mark.parametrize("protected", _protected_patterns())
def test_pr_paths_filter_covers_protected_pattern(protected: str) -> None:
    filters = [_github_glob_to_regex(p) for p in _pr_paths()]
    samples = _samples(protected)
    assert samples, protected
    uncovered = [s for s in samples if not any(f.match(s) for f in filters)]
    assert not uncovered, (
        f"protected pattern {protected!r}: PR touching {uncovered} would not "
        "trigger the L11 workflow (pull_request.paths)"
    )
