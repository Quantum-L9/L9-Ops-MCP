#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

from validate_helpers import ROOT, read, status_line

ALLOWED = "Quantum-L9"
FORBIDDEN_PATTERNS = [r"github\.com/cryptoxdog/[A-Za-z0-9_.-]+", r"owner:\s*cryptoxdog"]


def _org_invariants(text: str) -> dict[str, Any] | None:
    """Return the parsed ``org_invariants`` mapping, or None when absent."""
    for document in yaml.safe_load_all(text):
        if isinstance(document, dict) and isinstance(document.get("org_invariants"), dict):
            return document["org_invariants"]
    return None


def check_owner_invariant(text: str) -> list[str]:
    """Structural owner checks; a comment or prose mention does not count."""
    try:
        block = _org_invariants(text)
    except yaml.YAMLError as exc:
        return [f"invalid YAML: {exc}"]
    if block is None:
        return ["missing org_invariants mapping"]
    problems: list[str] = []
    if block.get("owner") != ALLOWED:
        problems.append(f"org_invariants.owner is {block.get('owner')!r}, expected {ALLOWED!r}")
    birth = block.get("repo_birth")
    allowed = birth.get("allowed_owner") if isinstance(birth, dict) else None
    if allowed != ALLOWED:
        problems.append(
            f"org_invariants.repo_birth.allowed_owner is {allowed!r}, expected {ALLOWED!r}"
        )
    return problems


def _report_owner_invariant(policy: Path) -> int:
    """Print the owner-invariant verdict; return the number of FAIL lines."""
    problems = check_owner_invariant(read(policy))
    for problem in problems:
        print(status_line("FAIL", "ORG_INVARIANTS.yaml", problem))
    if not problems:
        print(status_line("PASS", "ORG_INVARIANTS.yaml", "Quantum-L9 owner invariant present"))
    return len(problems)


def _scan_file(path: Path, root: Path) -> int:
    """Print a FAIL line per forbidden owner pattern in ``path``; return the count."""
    body = read(path)
    failures = 0
    for pat in FORBIDDEN_PATTERNS:
        if re.search(pat, body):
            print(
                status_line(
                    "FAIL",
                    str(path.relative_to(root)),
                    f"forbidden repo owner pattern: {pat}",
                )
            )
            failures += 1
    return failures


def _scan_forbidden_owners(root: Path) -> int:
    failures = 0
    scan_roots = [root / "playbooks", root / "docs", root / "schemas"]
    for base in scan_roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".yaml", ".yml", ".json"}:
                failures += _scan_file(path, root)
    return failures


def main(root: Path = ROOT) -> int:
    policy = root / "ORG_INVARIANTS.yaml"
    if not policy.exists():
        print(status_line("FAIL", "ORG_INVARIANTS.yaml", "missing"))
        return 1
    failures = _report_owner_invariant(policy)
    failures += _scan_forbidden_owners(root)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
