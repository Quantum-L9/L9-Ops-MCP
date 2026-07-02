---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# L11 Debt Governance Pipeline — Operations Runbook v3.0

> **Audience:** On-call engineers, platform team  
> **Scope:** Incident response, maintenance, troubleshooting  
> **Last updated:** 2026-02-12

---

## 1. Architecture Overview

```
PR Event / Cron Schedule
        │
        ▼
┌──────────────────┐     ┌──────────────────┐
│  Deterministic    │────▶│  Debt Graph      │
│  Engine           │     │  (Neo4j/JSON)    │
│  [BLOCKS MERGE]   │     └──────────────────┘
└──────────────────┘              │
        │                         ▼
        │              ┌──────────────────┐
        │              │  Risk Scorer      │
        │              │  (5-factor model) │
        │              └──────────────────┘
        │                         │
        ▼                         ▼
┌──────────────────┐     ┌──────────────────┐
│  AI Enrichment    │     │  Auto-Fix Engine │
│  (Perplexity)     │     │  (Shadow Branch) │
│  [NON-BLOCKING]   │     │  [HITL APPROVAL] │
└──────────────────┘     └──────────────────┘
```

---

## 2. Incident Response Playbooks

### 2.1 Circuit Breaker Open (AI Layer)

**Symptom:** Log entry `circuit_breaker_open` appears; AI enrichment skipped.

**Impact:** LOW — Deterministic layer continues to block bad PRs. Only AI enrichment is paused.

**Steps:**

1. Check Perplexity API status: https://status.perplexity.ai
2. Verify API key is valid:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" \
     -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
     https://api.perplexity.ai/chat/completions
   ```
3. If API is down → wait for recovery (circuit breaker auto-resets after 300s cooldown)
4. If API key expired → rotate in GitHub Secrets → re-run workflow
5. If persistent → check monthly budget cap in `01-L11-PIPELINE-CONFIG.yaml`

**Resolution:** Circuit breaker resets automatically. No manual intervention required unless API key is invalid.

---

### 2.2 Neo4j Connection Failure

**Symptom:** Log entry `neo4j_health_failed`; debt graph falls back to JSON.

**Impact:** MEDIUM — Findings tracked in `.l11/debt_findings.json` fallback. Regressions and aging still detected from JSON.

**Steps:**

1. Check Neo4j AuraDB console: https://console.neo4j.io
2. Verify credentials:
   ```bash
   echo $NEO4J_URI $NEO4J_USER
   cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" "RETURN 1"
   ```
3. If credentials rotated → update GitHub Secrets
4. If AuraDB free tier limits hit → upgrade or reduce query frequency
5. After recovery → backfill from JSON fallback:
   ```bash
   python scripts/l11_backfill_from_json.py --json-path .l11/debt_findings.json
   ```

---

### 2.3 Deterministic Engine False Positive

**Symptom:** PR blocked by a finding that is actually correct code.

**Impact:** HIGH — Blocks developer velocity.

**Steps:**

1. Identify the finding tool and rule from CI logs
2. Add inline suppression if justified:
   ```python
   x = some_expression  # noqa: ADR-0019  -- justified because ...
   ```
3. If systemic → update thresholds in `01-L11-PIPELINE-CONFIG.yaml`:
   ```yaml
   complexity_threshold:
     max_cyclomatic: 20  # Was 15; raised after audit
   ```
4. File a tuning issue: `gh issue create --title "L11: Tune [rule] threshold" --label "debt:tuning"`
5. Track false positive rate in Grafana

---

### 2.4 Auto-Fix Test Failure

**Symptom:** Log entry `auto_fix_rolled_back reason=tests_failed`

**Impact:** LOW — Auto-fix rolled back cleanly; no code changes merged.

**Steps:**

1. Confirm shadow branch was deleted:
   ```bash
   git branch -r | grep auto-fix/
   ```
2. Check test failure details in CI artifact `l11-deterministic-report`
3. If fix was correct but tests are flaky → fix the tests first
4. If fix was wrong → mark the finding category as unsupported:
   ```yaml
   # In 01-L11-PIPELINE-CONFIG.yaml
   supported_categories:
     # - docstring_missing  # Disabled: auto-fix unreliable
   ```

---

## 3. Maintenance Procedures

### 3.1 Weekly Health Check

```bash
# Check all components
python -c "
import asyncio
from 02_L11_ORCHESTRATOR import L11Orchestrator
from pathlib import Path
orch = L11Orchestrator(Path('01-L11-PIPELINE-CONFIG.yaml'))
result = asyncio.run(orch.health_check())
print(result)
"
```

### 3.2 Monthly Threshold Review

1. Query debt graph for false positive rate:
   ```cypher
   MATCH (f:Finding)
   WHERE f.status = 'accepted'
     AND f.first_seen > datetime() - duration('P30D')
   RETURN count(f) AS false_positives
   ```
2. If false_positive_rate > 5% → tune thresholds
3. Review aging policy escalations:
   ```cypher
   MATCH (f:Finding)
   WHERE f.severity = 'P0'
     AND f.first_seen > datetime() - duration('P30D')
   RETURN f.message, f.file, f.first_seen
   ```

### 3.3 Quarterly Cost Audit

| Check | Command |
|-------|---------|
| Perplexity API spend | Check billing dashboard |
| Neo4j storage | `CALL db.stats.retrieve("STORE")` |
| GitHub Actions minutes | Settings → Billing → Actions |
| Total | Sum all three |

Target: <$120/month total.

---

## 4. Configuration Reference

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PERPLEXITY_API_KEY` | Yes (for AI) | Perplexity API key |
| `NEO4J_URI` | Yes (for graph) | Neo4j connection URI |
| `NEO4J_USER` | Yes (for graph) | Neo4j username |
| `NEO4J_PASSWORD` | Yes (for graph) | Neo4j password |
| `SLACK_WEBHOOK_URL` | Optional | Slack notifications |

### Key Thresholds

| Threshold | Default | Effect |
|-----------|---------|--------|
| `block_pr` | 85 | Risk score ≥ 85 blocks merge |
| `create_issue` | 65 | Risk score ≥ 65 creates GitHub issue |
| `backlog` | 40 | Risk score ≥ 40 adds to backlog |
| `max_cyclomatic` | 15 | Cyclomatic complexity limit |
| `min_coverage_percent` | 80 | Test coverage floor |
| `circuit_breaker.failure_threshold` | 5 | AI failures before circuit opens |
| `circuit_breaker.cooldown_seconds` | 300 | Seconds before circuit half-opens |
| `monthly_budget_usd` | 100 | Perplexity API budget cap |

---

## 5. Escalation Matrix

| Severity | Response Time | Escalation |
|----------|---------------|------------|
| P0 — Critical | 1 hour | Slack #l9-critical-alerts → On-call engineer |
| P1 — High | 4 hours | Slack #l9-engineering → Team lead |
| P2 — Medium | 48 hours | GitHub issue auto-created |
| P3 — Low | Backlog | Added to sprint planning |

---

## 6. Rollback Procedures

### Full Pipeline Rollback

```bash
# Disable L11 workflow
gh workflow disable "L11 Debt Governance"

# Or disable specific jobs in the YAML
# Set `if: false` on the job you want to skip
```

### Component-Level Disable

```yaml
# In 01-L11-PIPELINE-CONFIG.yaml:

# Disable AI enrichment
detection:
  ai_layer:
    role: enrichment_and_classification
    blocks_merge: false
    # Set model to empty string to skip API calls

# Disable auto-fix
remediation:
  auto_fix:
    enabled: false
```
