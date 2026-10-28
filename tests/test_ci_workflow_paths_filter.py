"""OBS-02: the L11 workflow's ``pull_request.paths`` filter must reach every
protected path, otherwise a PR touching only a protected file (``Makefile``,
``.pre-commit-config.yaml``, ...) never runs the protected-files gate.

Matching follows GitHub's filter-pattern cheat sheet: ``*`` matches any run of
characters except ``/``, ``**`` matches any run including ``/``, ``?`` matches
one character. Each protected pattern is instantiated into concrete sample
paths, and every sample must be matched by some ``paths`` entry.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "08-L11-CI-WORKFLOW-v3.3.yaml"
POLICY = REPO_ROOT / "config" / "policies" / "protected_files.yaml"


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


def _protected_patterns() -> list[str]:
    policy = yaml.safe_load(POLICY.read_text())
    patterns: list[str] = []
    for category in policy["categories"].values():
        patterns.extend(category.get("protected_paths", []) or [])
        for sub in (category.get("subsystems") or {}).values():
            patterns.extend(sub.get("paths", []) or [])
    patterns.extend(policy.get("meta_protected_files", []) or [])
    patterns.append(".pre-commit-config.yaml")
    return sorted(set(patterns))


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
