#!/usr/bin/env bash
# >>> l9:meta >>>
# id: L9-Ops-MCP.script.scripts_enforce_progressive_disclosure__sh
# title: enforce progressive disclosure
# artifact_type: script
# mcp_primitive: none
# callable: false
# retrievable: false
# injectable: false
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: scripts/enforce_progressive_disclosure.sh
# content_hash: d68647d4bdba28c1263b6bab14e18005fe3b608b15f7742104722536f14cfa4c
# token_cost_estimate: 236
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
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
