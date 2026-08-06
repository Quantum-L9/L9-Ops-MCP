#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail=0
warn=0
check_len() {
  local file="$1" limit="$2" lines
  lines=$(wc -l < "$file" | tr -d ' ')
  if [ "$lines" -gt "$limit" ]; then echo "WARN: $file has $lines lines > $limit"; warn=$((warn+1)); fi
}
while IFS= read -r -d '' f; do check_len "$f" 500; done < <(find "$ROOT/skills" -name SKILL.md -print0 2>/dev/null)
while IFS= read -r -d '' f; do
  if grep -Eq "\]\([^)]*/references/[^)]*/" "$f"; then echo "FAIL: nested reference path in $f"; fail=$((fail+1)); fi
done < <(find "$ROOT/skills" -name SKILL.md -print0 2>/dev/null)
while IFS= read -r -d '' d; do
  if [ -f "$d/PLAYBOOK.md" ] && [ ! -d "$d/steps" ]; then echo "WARN: playbook has no steps directory: $d"; warn=$((warn+1)); fi
done < <(find "$ROOT/playbooks" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null)
echo "progressive_disclosure: fail=$fail warn=$warn"
exit "$fail"
