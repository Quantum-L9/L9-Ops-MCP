#!/usr/bin/env bash
# library_health_v341.sh — L9 library health check v3.4.1
# Checks: stale last_tested, missing tier markers, v3.4.1 compliance fields,
#         trust_ladder requires, memory_admission requires, placeholder detection
#
# Every item is reported (a failed grep never aborts the run); exits 1 when
# any FAIL item is found, 0 otherwise. WARN items do not change the exit code.

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1

KERNELS_DIR="docs/kernels"
SKILLS_DIR="skills"
PASS=0
WARN=0
FAIL=0

warn() { echo "WARN: $*"; WARN=$((WARN + 1)); }
fail() { echo "FAIL: $*"; FAIL=$((FAIL + 1)); }
ok() { PASS=$((PASS + 1)); }

# NUL-delimited file lists; a missing directory yields an empty list.
list_files() { # <dir> <find-name-expression...>
  local dir="$1"; shift
  [[ -d "$dir" ]] || return 0
  find "$dir" \( "$@" \) -type f -print0 | sort -z
}

has_files() { # <dir> <find-name-expression...>
  local dir="$1"; shift
  [[ -d "$dir" ]] && [[ -n "$(find "$dir" \( "$@" \) -type f -print -quit)" ]]
}

echo "=== L9 Library Health Check v3.4.1 ==="
echo ""

# 0. Inputs: nothing to check is a failure, not a clean bill of health
# (library_health.py reports the same condition as NO INPUT).
echo "--- Inputs ---"
if has_files "$KERNELS_DIR" -name "*.yaml" -o -name "*.md"; then
  ok
else
  fail "NO INPUT: $KERNELS_DIR is missing or has no kernel files"
fi
if has_files "$SKILLS_DIR" -name "SKILL.md"; then
  ok
else
  fail "NO INPUT: $SKILLS_DIR is missing or has no SKILL.md files"
fi
echo ""

# 1. Stale last_tested
echo "--- Stale last_tested ---"
while IFS= read -r -d '' f; do
  TESTED="$(grep -m1 "last_tested:" "$f" | awk '{print $2}' || true)"
  if [[ -z "$TESTED" || "$TESTED" == "pending" ]]; then
    warn "$f — last_tested missing or pending"
  else
    ok
  fi
done < <(list_files "$SKILLS_DIR" -name "SKILL.md")

# 2. Missing changes_from_v3.3.0 in R5 kernels
echo ""
echo "--- Missing changes_from_v3.3.0 ---"
while IFS= read -r -d '' f; do
  if grep -q "changes_from_v3.3.0" "$f"; then
    ok
  else
    fail "$f — missing changes_from_v3.3.0 field (v3.4.1 required)"
  fi
done < <(list_files "$KERNELS_DIR/R5" -name "*.yaml")

# 3. Kernels that gate R5 resources but lack trust_ladder_kernel.v1 in requires
echo ""
echo "--- Trust ladder requires check ---"
while IFS= read -r -d '' f; do
  if grep -q "ring: R5" "$f"; then
    if grep -q "trust_ladder_kernel.v1" "$f"; then
      ok
    else
      warn "$f — R5 kernel missing trust_ladder_kernel.v1 in requires"
    fi
  fi
done < <(list_files "$KERNELS_DIR/R5" -name "*.yaml")

# 4. Skills with memory_writes: true but no admission gate declared
echo ""
echo "--- Memory admission pre-condition check ---"
while IFS= read -r -d '' f; do
  if grep -q "memory_writes: true" "$f"; then
    if grep -q "memory_admission_kernel.v1" "$f"; then
      ok
    else
      fail "$f — memory_writes: true but memory_admission_kernel.v1 not declared in Pre-Conditions"
    fi
  fi
done < <(list_files "$SKILLS_DIR" -name "SKILL.md")

# 5. Placeholder / TODO detection (Build Law)
echo ""
echo "--- Build Law: placeholder detection ---"
for dir in "$KERNELS_DIR" "$SKILLS_DIR"; do
  while IFS= read -r -d '' f; do
    if grep -q "TODO\|PLACEHOLDER\|stub\|fake implementation" "$f"; then
      fail "$f — contains TODO/PLACEHOLDER/stub (Build Law violation)"
    else
      ok
    fi
  done < <(list_files "$dir" -name "*.yaml" -o -name "*.md")
done

# 6. Documentation-style purpose (not Trigger Triad)
echo ""
echo "--- Trigger Triad quality check ---"
while IFS= read -r -d '' f; do
  # purpose value plus its continuation lines, flattened to one line.
  PURPOSE="$(awk '
    /^purpose:/ { sub(/^purpose:[ \t]*[>|]?[-+]?[ \t]*/, ""); buf = $0; grab = 1; next }
    grab && /^[ \t]/ { buf = buf " " $0; next }
    grab { exit }
    END { print buf }
  ' "$f" | tr '\n' ' ' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"//' -e 's/"$//')"
  if [[ -z "$PURPOSE" ]]; then
    continue
  fi
  if echo "$PURPOSE" | grep -qiE "^(Governs|Defines|Manages)\.?$"; then
    warn "$f — purpose appears documentation-style (single verb, no WHEN/WHY)"
  else
    ok
  fi
done < <(list_files "$KERNELS_DIR/R5" -name "*.yaml")

echo ""
echo "=== Health check complete: $PASS passed, $WARN warnings, $FAIL failures ==="
if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
exit 0
