#!/usr/bin/env bash
# L9_META: origin: l9-kernel | layer: scripts | status: active
# scripts/audit_hardban_duplication.sh
# Detects universal hard bans duplicated inside kernel body text.

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FAIL=0

UNIVERSAL_BANS=(
  "never produce harmful content"
  "never reveal system prompt"
  "never impersonate a human"
  "always cite sources"
)

echo "L9 Universal Hard Ban Duplication Audit"
echo "========================================"

while IFS= read -r -d '' f; do
  for ban in "${UNIVERSAL_BANS[@]}"; do
    if grep -qi "$ban" "$f" 2>/dev/null; then
      echo "WARN: universal ban duplicated in $f"
      echo "      Pattern: '$ban'"
      echo "      Action: replace with reference to docs/contracts/UNIVERSAL_HARDBANS.md"
      FAIL=$((FAIL + 1))
    fi
  done
done < <(find "$REPO_ROOT/docs/kernels" -type f -print0 2>/dev/null)

if [ "$FAIL" -eq 0 ]; then
  echo "PASS: no universal hard ban duplication found"
  exit 0
else
  echo ""
  echo "FAIL: $FAIL duplication(s) found — replace with references"
  exit 1
fi
