#!/usr/bin/env bash
# l9-ops: Progressive Disclosure Enforcement
set -uo pipefail

LIBRARY_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KERNEL_DIR="$LIBRARY_ROOT/kernels/optimized"
EXIT_CODE=0
VIOLATIONS=0
KERNEL_COUNT=0

echo "======================================================="
echo "  l9-ops Progressive Disclosure Enforcement"
echo "  $(date +%Y-%m-%d)"
echo "======================================================="

audit_kernel() {
  local kernel_file="$1"
  local fname
  fname=$(basename "$kernel_file")
  local violations=0

  if ! grep -q "tier2_load:" "$kernel_file" 2>/dev/null; then
    echo "  FAIL MISSING tier2_load in $fname"; violations=$((violations+1))
  fi
  if ! grep -q "tier3_load:" "$kernel_file" 2>/dev/null; then
    echo "  FAIL MISSING tier3_load in $fname"; violations=$((violations+1))
  fi
  if ! grep -q "Use when:" "$kernel_file" 2>/dev/null; then
    echo "  FAIL MISSING Trigger Triad in $fname"; violations=$((violations+1))
  fi
  if ! grep -q "lastRunDate:" "$kernel_file" 2>/dev/null; then
    echo "  WARN lastRunDate absent in $fname"
  fi

  # TRUE Tier-3 analytics must appear AFTER tier3_load.
  # convergence_footer + routing_hints are runtime analytics (Tier 3).
  local tier3_line
  tier3_line=$(grep -n "tier3_load:" "$kernel_file" 2>/dev/null | head -1 | cut -d: -f1 || true)
  if [ -n "$tier3_line" ]; then
    for t3_marker in "convergence_footer:" "routing_hints:"; do
      local marker_line
      marker_line=$(grep -n "^${t3_marker}" "$kernel_file" 2>/dev/null | head -1 | cut -d: -f1 || true)
      if [ -n "$marker_line" ] && [ "$marker_line" -lt "$tier3_line" ] 2>/dev/null; then
        echo "  FAIL TIER3 BLEED: $t3_marker at line $marker_line before tier3_load at $tier3_line in $fname"
        violations=$((violations+1))
      fi
    done
  fi

  if [ $violations -eq 0 ]; then
    echo "  PASS: $fname"
  else
    VIOLATIONS=$((VIOLATIONS+violations)); EXIT_CODE=1
  fi
}

while IFS= read -r kernel_file; do
  KERNEL_COUNT=$((KERNEL_COUNT+1))
  audit_kernel "$kernel_file"
done < <(find "$KERNEL_DIR" -name "*.yaml" 2>/dev/null | sort)

echo ""
echo "Kernels audited: $KERNEL_COUNT | Violations: $VIOLATIONS"
echo "======================================================="
if [ $EXIT_CODE -eq 0 ]; then
  echo "  Progressive Disclosure: PASS"
else
  echo "  Progressive Disclosure: FAIL ($VIOLATIONS)"
fi
echo "======================================================="
exit $EXIT_CODE
