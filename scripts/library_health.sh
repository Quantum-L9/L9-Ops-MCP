#!/usr/bin/env bash
# L9_META: origin: l9-kernel | layer: scripts | status: active
# scripts/library_health.sh — harness health check
# Detects: stale kernels, missing eval_status, harness copies outside canonical paths,
#          missing tier markers, and monolithic playbooks.

set -euo pipefail

PASS=0
FAIL=0
WARN=0
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TODAY=$(date +%Y-%m-%d)
STALE_DAYS=30

echo "═══════════════════════════════════════════════"
echo " L9 Library Health Check — $TODAY"
echo " Repo: $REPO_ROOT"
echo "═══════════════════════════════════════════════"

# ── 1. Harness copy sprawl check ────────────────────────────────────────
echo ""
echo "── [1] Harness copy sprawl"
CANONICAL_CODING="docs/kernels/R5/l9_coding_kernel.v1.md"
CANONICAL_BUILD="docs/kernels/R5/l9_build_kernel.v1.md"

copies=$(find "$REPO_ROOT" -type f \( -name "l9_coding_kernel*" -o -name "l9_build_kernel*" \) \
  ! -path "*/$CANONICAL_CODING" \
  ! -path "*/$CANONICAL_BUILD" \
  ! -path "*/archive/*" 2>/dev/null | wc -l)

if [ "$copies" -gt 0 ]; then
  echo "  FAIL: $copies harness kernel copy/copies found outside canonical paths"
  find "$REPO_ROOT" -type f \( -name "l9_coding_kernel*" -o -name "l9_build_kernel*" \) \
    ! -path "*/$CANONICAL_CODING" ! -path "*/$CANONICAL_BUILD" ! -path "*/archive/*" 2>/dev/null
  FAIL=$((FAIL + 1))
else
  echo "  PASS: no harness copies outside canonical paths"
  PASS=$((PASS + 1))
fi

# ── 2. Stale last_tested check ───────────────────────────────────────────
echo ""
echo "── [2] Stale last_tested dates (> ${STALE_DAYS} days)"
stale_count=0
while IFS= read -r -d '' f; do
  if grep -q "last_tested:" "$f" 2>/dev/null; then
    tested=$(grep "last_tested:" "$f" | head -1 | sed 's/.*last_tested:[ "]*//' | tr -d '"' | xargs)
    if [[ -n "$tested" ]]; then
      # Skip date math if `date -d` not available (macOS fallback)
      age=$(( ($(date -d "$TODAY" +%s 2>/dev/null || date -j -f "%Y-%m-%d" "$TODAY" +%s) - $(date -d "$tested" +%s 2>/dev/null || date -j -f "%Y-%m-%d" "$tested" +%s)) / 86400 )) 2>/dev/null || age=0
      if [ "${age:-0}" -gt "$STALE_DAYS" ]; then
        echo "  WARN: $f — last_tested: $tested (${age}d ago)"
        WARN=$((WARN + 1))
        stale_count=$((stale_count + 1))
      fi
    fi
  fi
done < <(find "$REPO_ROOT/docs/kernels" -type f -print0 2>/dev/null)

if [ "$stale_count" -eq 0 ]; then
  echo "  PASS: all kernels tested within ${STALE_DAYS} days"
  PASS=$((PASS + 1))
fi

# ── 3. Missing eval_status check ────────────────────────────────────────
echo ""
echo "── [3] Missing eval_status"
missing_eval=0
while IFS= read -r -d '' f; do
  if ! grep -q "eval_status:" "$f" 2>/dev/null; then
    echo "  FAIL: missing eval_status — $f"
    FAIL=$((FAIL + 1))
    missing_eval=$((missing_eval + 1))
  fi
done < <(find "$REPO_ROOT/docs/kernels" -type f -name "*.yaml" -o -name "*.md" -print0 2>/dev/null)

if [ "$missing_eval" -eq 0 ]; then
  echo "  PASS: all kernel files have eval_status"
  PASS=$((PASS + 1))
fi

# ── 4. Missing Tier 1 structure in R5+ kernels ──────────────────────────
echo ""
echo "── [4] Missing TIER 1 structure (R5+ kernels)"
missing_tier=0
while IFS= read -r -d '' f; do
  if ! grep -qi "tier 1" "$f" 2>/dev/null && ! grep -qi "tier1" "$f" 2>/dev/null; then
    echo "  WARN: missing TIER 1 section — $f"
    WARN=$((WARN + 1))
    missing_tier=$((missing_tier + 1))
  fi
done < <(find "$REPO_ROOT/docs/kernels/R5" -type f -print0 2>/dev/null)

if [ "$missing_tier" -eq 0 ]; then
  echo "  PASS: all R5 kernels have TIER 1 section"
  PASS=$((PASS + 1))
fi

# ── 5. Monolithic playbook check ────────────────────────────────────────
echo ""
echo "── [5] Monolithic playbooks (no steps/ directory)"
monolith=0
while IFS= read -r pb_dir; do
  if [ ! -d "$pb_dir/steps" ]; then
    echo "  WARN: playbook has no steps/ directory — $pb_dir"
    WARN=$((WARN + 1))
    monolith=$((monolith + 1))
  fi
done < <(find "$REPO_ROOT/playbooks" -maxdepth 1 -mindepth 1 -type d 2>/dev/null)

if [ "$monolith" -eq 0 ]; then
  echo "  PASS: all playbooks have steps/ directory"
  PASS=$((PASS + 1))
fi

# ── Summary ──────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════"
echo " Results: PASS=$PASS  WARN=$WARN  FAIL=$FAIL"
echo "═══════════════════════════════════════════════"

if [ "$FAIL" -gt 0 ]; then
  echo " STATUS: ❌ FAIL — $FAIL hard gate(s) failed"
  exit 1
elif [ "$WARN" -gt 0 ]; then
  echo " STATUS: ⚠️  WARN — $WARN advisory issue(s)"
  exit 0
else
  echo " STATUS: ✅ PASS — library is healthy"
  exit 0
fi
