---
l9_schema: 1
artifact_type: "documentation"
tags: ["docs"]
retrieval: "on_demand"
status: "active"
id: "L9-Ops-MCP.context.docs_branch_protection_settings__md"
title: "BRANCH PROTECTION SETTINGS"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/BRANCH-PROTECTION-SETTINGS.md"
content_hash: "bb70cc43ca833281729c58d25d43a7013333a3ef423212e14c86dc65ce56e59e"
token_cost_estimate: 369
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "auditor"
description: "Unknown"
activation_signals: ["check", "scan"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
---
# Branch Protection Settings for L9

> Apply these settings in GitHub → Settings → Branches → Add rule → `main`

## Required Status Checks

Enable: **Require status checks to pass before merging**

Add these required checks (must match job `name:` in `08-L11-CI-WORKFLOW.yaml`):

| Check Name | Blocks Merge | Source |
|---|---|---|
| `✅ Merge Gate` | Yes | L11 CI workflow (aggregates all gates) |
| `🔒 Deterministic Scan` | Yes | L11 deterministic layer |
| `🔐 Secrets Scan` | Yes | Gitleaks |
| `📋 L9 CI Scripts` | Yes | Existing L9 ci/ checks |
| `🧪 Tests + Coverage` | Yes | pytest + Codecov |
| `🔗 Integration Tests` | Yes | pytest integration |
| `🏗️ L11 Component Tests` | Yes | L11 self-tests |

### Optional (non-blocking, but visible):
| Check Name | Blocks Merge | Source |
|---|---|---|
| `🧠 AI Enrichment` | No | Perplexity debt enrichment |
| `📊 Debt Graph Update` | No | Neo4j upsert |
| CodeRabbit | Configurable | CodeRabbit GitHub App |

## Additional Settings

- **Require branches to be up to date before merging**: ✅ Enabled
- **Require conversation resolution before merging**: ✅ Enabled
- **Require review from Code Owners**: ✅ Enabled (uses CODEOWNERS file)
- **Dismiss stale pull request approvals when new commits are pushed**: ✅ Enabled
- **Restrict who can push to matching branches**: Admin only
- **Include administrators**: ✅ Enabled (admins also go through CI)
- **Allow force pushes**: ❌ Disabled
- **Allow deletions**: ❌ Disabled
