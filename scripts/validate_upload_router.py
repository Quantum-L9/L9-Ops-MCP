#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from validate_helpers import ROOT, read, status_line

REQUIRED = [
    "playbooks/github-upload-capture/PLAYBOOK.md",
    "playbooks/github-upload-capture/handoffs/upload_manifest.schema.yaml",
    "playbooks/github-upload-capture/handoffs/repo_route_decision.schema.yaml",
    "playbooks/github-upload-capture/handoffs/context_slice_request.schema.yaml",
    "schemas/repo_route_decision.schema.yaml",
    "ORG_INVARIANTS.yaml",
]


def main() -> int:
    failures = 0
    for rel_path in REQUIRED:
        path = ROOT / rel_path
        if not path.exists():
            print(status_line("FAIL", rel_path, "missing")); failures += 1
        else:
            print(status_line("PASS", rel_path, "exists"))
    route_schema = read(ROOT / "schemas" / "repo_route_decision.schema.yaml")
    for marker in ["new_repo", "existing_repo_pr", "archive_only", "Quantum-L9"]:
        if marker not in route_schema:
            print(status_line("FAIL", "schemas/repo_route_decision.schema.yaml", f"missing {marker}")); failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
