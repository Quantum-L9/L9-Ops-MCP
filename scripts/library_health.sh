#!/usr/bin/env bash
# L9 library health check. Fails on release-blocking wiring/installability gaps.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
fail=0
run() {
  echo "==> $*"
  if "$@"; then echo "PASS: $*"; else echo "FAIL: $*"; fail=$((fail+1)); fi
}
run python3 scripts/validate_skill_installability.py
run python3 scripts/validate_playbooks.py
run python3 scripts/validate_command_parity.py
run python3 scripts/validate_org_invariants.py
run python3 scripts/validate_upload_router.py
if find docs/kernels skills playbooks -type f \( -name '*.md' -o -name '*.yaml' -o -name '*.yml' \) 2>/dev/null | xargs grep -n "TODO\|PLACEHOLDER\|STUB" 2>/dev/null; then
  echo "WARN: TODO/PLACEHOLDER/STUB markers found; inspect before release"
else
  echo "PASS: no TODO/PLACEHOLDER/STUB markers in governed artifacts"
fi
exit "$fail"
