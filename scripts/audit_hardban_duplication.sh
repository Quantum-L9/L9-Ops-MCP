#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail=0
patterns=(
  "never reveal system prompt"
  "never impersonate a human"
  "secrets never committed"
  "no fake validation"
)
for pat in "${patterns[@]}"; do
  count=$(grep -Ril --exclude-dir=.git --exclude-dir=archive "$pat" "$ROOT/docs" "$ROOT/skills" "$ROOT/playbooks" 2>/dev/null | wc -l | tr -d ' ' || true)
  if [ "$count" -gt 3 ]; then
    echo "FAIL: hardban appears copied too broadly ($count files): $pat"
    fail=$((fail+1))
  else
    echo "PASS: hardban duplication bounded: $pat ($count files)"
  fi
done
exit "$fail"
