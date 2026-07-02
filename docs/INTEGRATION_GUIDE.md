---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# Protected Files Enforcement v6.0 — L11 Integration Guide
#
# This doc specifies how to integrate the Protected Files Enforcement Spec v6.0
# into the existing L11 Debt Governance Pipeline (v3.2).
#
# Produces:
#   1. config/policies/protected_files.yaml — policy source of truth
#   2. .github/scripts/validate-protected-files-v6.py — CI validator
#   3. Updated CI workflow (v3.3) with "🛡️ Protected Files Gate" job
#   4. Updated DEPLOY.sh (v3.3) with ruleset including the new gate
#   5. Nightly drift reconciliation job
#
# Integration strategy: ADDITIVE. No existing jobs modified.
# One new blocking job + one nightly job added.

## What already exists in L9

The repo already has these components that the spec references:

| Component | Path | Status |
|-----------|------|--------|
| Policy loader | `core/governance/protected_files_policy.py` | EXISTS — has `load_protected_files_policy()`, `is_protected()`, `is_lcto_controlled()` |
| CI validator (v1) | `ci/check_protected_files.py` | EXISTS — older version, checks `IGOR_APPROVED` in commit msg |
| GitHub script (v1) | `.github/scripts/validate-protected-files.py` | EXISTS — 142 lines, basic version |

The spec v6 **replaces** the GitHub script with a v6 version and **adds** the YAML policy.
The existing `core/governance/protected_files_policy.py` loader is kept — v6 validator imports it.

## Integration Architecture

```
L11 CI Workflow v3.3
├── Lint, typecheck, test-fast      (existing, blocking)
├── ADR Compliance                  (existing, blocking)
├── CI Gates                        (existing, blocking)
├── 🔐 Secrets Scan                 (existing, blocking)
├── 🧪 Tests + Coverage             (existing, blocking)
├── 🏗️ L11 Component Tests          (existing, blocking)
├── 🛡️ Protected Files Gate    ←── NEW (blocking)
├── ✅ Merge Gate                    (existing, aggregates ALL above)
├── 🤖 AI Enrichment                (existing, non-blocking)
├── 📊 Debt Graph Update            (existing, non-blocking)
├── 🌙 Nightly Maintenance          (existing, nightly)
└── 🔍 Drift Reconciliation    ←── NEW (nightly)
```
