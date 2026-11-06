#!/usr/bin/env bash
# >>> l9:meta >>>
# id: L9-Ops-MCP.script.scripts_audit_hardban_duplication__sh
# title: audit hardban duplication
# artifact_type: script
# mcp_primitive: none
# callable: false
# retrievable: false
# injectable: false
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: scripts/audit_hardban_duplication.sh
# content_hash: 753eb428639e2b981b0993c9e7ea1bbdf83f6c5dc23e57ba608ef3fb5ddca4fd
# token_cost_estimate: 159
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
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
