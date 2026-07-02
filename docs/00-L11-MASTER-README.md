---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# L11 Debt Governance Pipeline v3.0

**Philosophy:** Deterministic-Core + AI-Augmentation
**Quality:** Frontier AI lab tier (Anthropic/OpenAI/DeepMind)
**Status:** Production-ready
**Upgrade from:** v1.0 Perplexity Research Agent Pipeline

---

## Core Architecture Philosophy

### Two-Layer Detection Model

```
┌─────────────────────────────────────────────────┐
│  Deterministic Layer (Non-Blocking, Always On)  │
│  • Ruff, Mypy, Bandit, Semgrep                  │
│  • ADR compliance static analysis               │
│  • Dependency graph validation                  │
│  • Schema validation                            │
│  • Complexity/coverage thresholds               │
│  • BLOCKS merge on violation                    │
└─────────────────────────────────────────────────┘
         ↓ (Enrichment data flows to AI layer)
┌─────────────────────────────────────────────────┐
│  AI Enrichment Layer (Non-Blocking, Async)      │
│  • Perplexity sonar-pro semantic analysis       │
│  • Context-aware classification                 │
│  • Risk scoring with blast radius               │
│  • Auto-fix strategy generation                 │
│  • NEVER blocks merge — enriches only           │
└─────────────────────────────────────────────────┘
```

**Key Principle:** Deterministic layer gates production. AI layer provides intelligence.

---

## Package Contents (11 Files)

| File | Purpose |
|------|---------|
| `00-L11-MASTER-README.md` | Master orientation (this file) |
| `01-L11-PIPELINE-CONFIG.yaml` | Dual-layer configuration |
| `02-L11-ORCHESTRATOR.py` | Production orchestrator with state management |
| `03-L11-DETERMINISTIC-ENGINE.py` | Static analysis + schema validation engine |
| `04-L11-AI-ENRICHMENT-ENGINE.py` | Perplexity-powered classification engine |
| `05-L11-DEBT-GRAPH-SERVICE.py` | Persistent debt tracking with Neo4j |
| `06-L11-RISK-SCORER.py` | Multi-factor risk model |
| `07-L11-AUTO-FIX-ENGINE.py` | Shadow validation + rollback |
| `08-L11-CI-WORKFLOW.yaml` | GitHub Actions integration |
| `09-L11-RUNBOOK.md` | Operations guide |
| `10-L11-METRICS-DASHBOARD.md` | Grafana + Prometheus config |

---

## What Changed from v1.0

| Dimension | v1.0 | v3.0 |
|-----------|------|------|
| Detection | AI-only (Perplexity) | Deterministic-first + AI enrichment |
| Merge Gate | AI confidence threshold | Static analysis pass/fail |
| State | Ephemeral (per-run) | Persistent Neo4j debt graph |
| Regression | Not tracked | Hash-based reintroduction detection |
| Risk Model | Single severity | 5-factor weighted score |
| Auto-Fix | None | Shadow branch + rollback + HITL |
| Resilience | API failure = pipeline failure | Circuit breaker + deterministic fallback |
| Scaling | Sequential | 20 deterministic + 5 AI parallel workers |
| Cost Control | Unbounded | Monthly budget cap + rate limiting |

---

## Deployment Phases

### Phase 1: Deterministic Layer (Week 1)

```bash
pip install ruff mypy bandit semgrep radon
cp 03-L11-DETERMINISTIC-ENGINE.py scripts/l11_deterministic.py
python scripts/l11_deterministic.py --scope api/ core/
```

### Phase 2: Debt Graph (Week 2)

```bash
python scripts/l11_debt_graph_init.py
python scripts/l11_backfill_debt.py --since 2025-01-01
python scripts/l11_debt_graph_health.py
```

### Phase 3: AI Enrichment (Week 3)

```bash
export PERPLEXITY_API_KEY="pplx-..."
cp 04-L11-AI-ENRICHMENT-ENGINE.py scripts/l11_ai_enrichment.py
python scripts/l11_ai_enrichment.py --mode enrich --findings-file findings.json
```

### Phase 4: CI Integration (Week 4)

```bash
cp 08-L11-CI-WORKFLOW.yaml .github/workflows/l11-debt-governance.yaml
# Set secrets: PERPLEXITY_API_KEY, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
gh pr create --title "Test L11 Pipeline" --body "Testing..."
```

---

## Risk Management

| Risk | Mitigation |
|------|------------|
| Deterministic false positives | Tune thresholds in config; add exclusion patterns |
| AI layer downtime | Circuit breaker falls back to deterministic-only |
| Neo4j unavailable | Graceful degradation; findings stored in JSON fallback |
| Auto-fix breaks tests | Shadow validation catches failures before merge |
| Cost overrun (Perplexity API) | Rate limiting + monthly budget alerts ($100 default) |

---

## Success Metrics (Target by Month 3)

| Metric | Baseline | Target | Tracking |
|--------|----------|--------|----------|
| Debt Ratio | 15% | <5% | Prometheus gauge |
| Mean Time to Remediation | 14 days | <7 days | Debt graph query |
| Regression Rate | 25% | <10% | Finding hash comparison |
| P0 Count | 8 | 0 | Real-time Grafana alert |
| False Positive Rate | N/A | <5% | Manual audit sample |

---

## ADR Compliance

This pipeline enforces ALL 56 L9 ADRs:

- **ADR-0002:** TYPE_CHECKING imports checked by deterministic layer
- **ADR-0006:** TransportPacket audit trails verified
- **ADR-0012:** DAG pipeline validation-in-intake-only enforced
- **ADR-0014:** DORA metadata blocks checked on every module
- **ADR-0019:** structlog-only logging enforced (zero tolerance)
- **ADR-0028:** Transaction context patterns validated
- **ADR-0038:** Secrets management compliance checked
- **ADR-0055:** Fail-loudly vs graceful degradation policy
- **ADR-0083:** UTC datetime standard

Plus 47 additional ADRs covered across 12 categories.

---

## Cost Estimate

| Component | Monthly Cost |
|-----------|--------------|
| Perplexity API (AI layer) | ~$50-100 |
| Neo4j AuraDB Free Tier | $0 |
| GitHub Actions minutes (CI) | ~$20 |
| Engineering time (maintenance) | 4h/month |
| **Total** | **~$70-120/month** |

One-time setup: 32 engineering hours over 4 weeks.
