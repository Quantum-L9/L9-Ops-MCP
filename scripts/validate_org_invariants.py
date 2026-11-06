#!/usr/bin/env python3
# >>> l9:meta >>>
# id: L9-Ops-MCP.script.scripts_validate_org_invariants__py
# title: validate org invariants
# artifact_type: script
# mcp_primitive: none
# callable: false
# retrievable: false
# injectable: false
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: scripts/validate_org_invariants.py
# content_hash: 1d7b6b40298b1bf9f16bab26202fc5b514401e26989cd6cc51d58fd7928d9be5
# token_cost_estimate: 398
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
from __future__ import annotations

import re
import sys
from validate_helpers import ROOT, read, status_line

ALLOWED = "Quantum-L9"
FORBIDDEN_PATTERNS = [r"github\.com/cryptoxdog/[A-Za-z0-9_.-]+", r"owner:\s*cryptoxdog"]


def main() -> int:
    policy = ROOT / "ORG_INVARIANTS.yaml"
    if not policy.exists():
        print(status_line("FAIL", "ORG_INVARIANTS.yaml", "missing"))
        return 1
    text = read(policy)
    failures = 0
    if f"owner: {ALLOWED}" not in text and f"allowed_owner: {ALLOWED}" not in text:
        print(status_line("FAIL", "ORG_INVARIANTS.yaml", "missing Quantum-L9 owner invariant"))
        failures += 1
    else:
        print(status_line("PASS", "ORG_INVARIANTS.yaml", "Quantum-L9 owner invariant present"))
    scan_roots = [ROOT / "playbooks", ROOT / "docs", ROOT / "schemas"]
    for base in scan_roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".yaml", ".yml", ".json"}:
                body = read(path)
                for pat in FORBIDDEN_PATTERNS:
                    if re.search(pat, body):
                        print(
                            status_line(
                                "FAIL",
                                str(path.relative_to(ROOT)),
                                f"forbidden repo owner pattern: {pat}",
                            )
                        )
                        failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
