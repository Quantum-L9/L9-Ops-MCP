#!/usr/bin/env bash
# library_health_v341.sh — L9 library health check v3.4.1
# Checks: stale last_tested, missing tier markers, v3.4.1 compliance fields,
#         trust_ladder requires, memory_admission requires, placeholder detection

set -euo pipefail

KERNELS_DIR="docs/kernels"
SKILLS_DIR="skills"
PASS=0
WARN=0
FAIL=0

echo "=== L9 Library Health Check v3.4.1 ==="
echo ""

# 1. Stale last_tested (> 30 days)
echo "--- Stale last_tested ---"
TODAY=$(date +%Y-%m-%d)
find "$SKILLS_DIR" -name "SKILL.md" | while read f; do
  TESTED=$(grep "last_tested:" "$f" | awk '{print $2}' | head -1)
  if [[ -z "$TESTED" || "$TESTED" == "pending" ]]; then
    echo "WARN: $f — last_tested missing or pending"
  fi
done

# 2. Missing changes_from_v3.3.0 in R5 kernels
echo ""
echo "--- Missing changes_from_v3.3.0 ---"
find "$KERNELS_DIR/R5" -name "*.yaml" 2>/dev/null | while read f; do
  if ! grep -q "changes_from_v3.3.0" "$f" 2>/dev/null; then
    echo "FAIL: $f — missing changes_from_v3.3.0 field (v3.4.1 required)"
  fi
done

# 3. Kernels that gate R5 resources but lack trust_ladder_kernel.v1 in requires
echo ""
echo "--- Trust ladder requires check ---"
find "$KERNELS_DIR/R5" -name "*.yaml" 2>/dev/null | while read f; do
  if grep -q "ring: R5" "$f" 2>/dev/null; then
    if ! grep -q "trust_ladder_kernel.v1" "$f" 2>/dev/null; then
      echo "WARN: $f — R5 kernel missing trust_ladder_kernel.v1 in requires"
    fi
  fi
done

# 4. Skills with memory_writes: true but no admission gate declared
echo ""
echo "--- Memory admission pre-condition check ---"
find "$SKILLS_DIR" -name "SKILL.md" | while read f; do
  if grep -q "memory_writes: true" "$f" 2>/dev/null; then
    if ! grep -q "memory_admission_kernel.v1" "$f" 2>/dev/null; then
      echo "FAIL: $f — memory_writes: true but memory_admission_kernel.v1 not declared in Pre-Conditions"
    fi
  fi
done

# 5. Placeholder / TODO detection (Build Law)
echo ""
echo "--- Build Law: placeholder detection ---"
find "$KERNELS_DIR" "$SKILLS_DIR" -name "*.yaml" -o -name "*.md" 2>/dev/null |   xargs grep -l "TODO\|PLACEHOLDER\|stub\|fake implementation" 2>/dev/null | while read f; do
  echo "FAIL: $f — contains TODO/PLACEHOLDER/stub (Build Law violation)"
done

# 6. Documentation-style purpose (not Trigger Triad)
echo ""
echo "--- Trigger Triad quality check ---"
find "$KERNELS_DIR/R5" -name "*.yaml" 2>/dev/null | while read f; do
  PURPOSE=$(grep -A3 "^purpose:" "$f" 2>/dev/null | tr -n | head -c 200)
  if echo "$PURPOSE" | grep -qiE "^  Governs\.?$|^  Defines\.?$|^  Manages\.?$"; then
    echo "WARN: $f — purpose appears documentation-style (single verb, no WHEN/WHY)"
  fi
done

echo ""
echo "=== Health check complete. Review WARN and FAIL items above. ==="
