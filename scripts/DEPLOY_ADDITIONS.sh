#!/usr/bin/env bash
# ── Add to Phase 3 of DEPLOY.sh ──

# ── Protected Files Policy (NEW — Spec v6) ──
cp protected_files.yaml config/policies/protected_files.yaml
echo "  ✅ config/policies/protected_files.yaml"

# ── Protected Files Validator v6 (NEW — replaces v1) ──
cp validate-protected-files-v6.py .github/scripts/validate-protected-files-v6.py
echo "  ✅ .github/scripts/validate-protected-files-v6.py"

# ── Replace Phase 5 ruleset with ──

gh api \
  --method POST \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "repos/cryptoxdog/L9/rulesets" \
  --input - << 'EOF'
{
  "name": "L11 Merge Protection v3.3",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "include": ["refs/heads/main"],
      "exclude": []
    }
  },
  "rules": [
    {
      "type": "pull_request",
      "parameters": {
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": true,
        "require_last_push_approval": false,
        "required_approving_review_count": 1,
        "required_review_thread_resolution": true
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [
          {"context": "Lint, typecheck, test-fast"},
          {"context": "ADR Compliance"},
          {"context": "CI Gates"},
          {"context": "🔐 Secrets Scan"},
          {"context": "🧪 Tests + Coverage"},
          {"context": "🏗️ L11 Component Tests"},
          {"context": "🛡️ Protected Files Gate"},
          {"context": "✅ Merge Gate"}
        ]
      }
    },
    {"type": "non_fast_forward"},
    {"type": "deletion"}
  ]
}
EOF
