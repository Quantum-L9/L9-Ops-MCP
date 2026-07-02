---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# L11 Debt Governance — Metrics & Dashboard Configuration v3.0

> **Audience:** Platform engineers, SRE  
> **Systems:** Prometheus + Grafana  
> **Dashboard UID:** `l11-debt`

---

## 1. Prometheus Metrics Specification

### 1.1 Core Debt Metrics

```yaml
# Exposed at /metrics/debt

# Gauge: Current open debt count by severity
- name: l11_debt_open_total
  type: gauge
  help: "Total open debt findings"
  labels: [severity]
  # severity: P0 | P1 | P2 | P3

# Gauge: Debt ratio (findings / total_lines_scanned)
- name: l11_debt_ratio
  type: gauge
  help: "Debt ratio as percentage"
  labels: [scope]
  # scope: core | api | agents | memory | workers

# Counter: Total findings discovered
- name: l11_findings_total
  type: counter
  help: "Cumulative findings discovered"
  labels: [tool, severity]
  # tool: ruff | mypy | bandit | semgrep | adr_checker | radon

# Counter: Regressions detected
- name: l11_regressions_total
  type: counter
  help: "Findings that were fixed then reintroduced"

# Histogram: Time from first_seen to status=fixed
- name: l11_remediation_duration_days
  type: histogram
  help: "Days from detection to remediation"
  buckets: [1, 3, 7, 14, 30, 60, 90]
```

### 1.2 Pipeline Performance Metrics

```yaml
# Histogram: Deterministic scan duration
- name: l11_deterministic_scan_duration_ms
  type: histogram
  help: "Deterministic engine scan latency"
  buckets: [500, 1000, 2000, 5000, 10000, 30000]

# Histogram: AI enrichment latency per finding
- name: l11_ai_enrichment_duration_ms
  type: histogram
  help: "AI enrichment latency per finding"
  buckets: [100, 500, 1000, 2000, 5000, 10000]

# Gauge: Circuit breaker state (0=closed, 1=half-open, 2=open)
- name: l11_circuit_breaker_state
  type: gauge
  help: "AI circuit breaker state"

# Counter: Circuit breaker trips
- name: l11_circuit_breaker_trips_total
  type: counter
  help: "Number of times circuit breaker opened"

# Counter: Auto-fix attempts and outcomes
- name: l11_autofix_attempts_total
  type: counter
  help: "Auto-fix attempts"
  labels: [outcome]
  # outcome: success | tests_failed | unsupported | disabled
```

### 1.3 Cost Metrics

```yaml
# Counter: Perplexity API calls
- name: l11_ai_api_calls_total
  type: counter
  help: "Perplexity API calls made"

# Gauge: Estimated monthly spend (USD)
- name: l11_ai_estimated_cost_usd
  type: gauge
  help: "Estimated Perplexity API spend this month"

# Gauge: Budget remaining
- name: l11_ai_budget_remaining_usd
  type: gauge
  help: "Remaining monthly AI budget"
```

---

## 2. Grafana Dashboard Panels

### Dashboard: `l11-debt` (UID: `l11-debt`)

**Folder:** L9-Governance  
**Refresh:** 1 minute  
**Time range:** Last 30 days

---

### Row 1: Executive Summary

#### Panel 1.1 — Debt Ratio Trend (Time Series)
```promql
l11_debt_ratio{scope="core"}
l11_debt_ratio{scope="api"}
l11_debt_ratio{scope="agents"}
```
- **Type:** Time series
- **Threshold:** Red line at 5% (target ceiling)
- **Alert:** Fire if > 10% for 24h

#### Panel 1.2 — P0 Count (Stat)
```promql
l11_debt_open_total{severity="P0"}
```
- **Type:** Stat (single value)
- **Threshold:** Green = 0, Red > 0
- **Alert:** CRITICAL if > 0 for 1h → Slack #l9-critical-alerts

#### Panel 1.3 — Total Open Debt (Stat)
```promql
sum(l11_debt_open_total)
```
- **Type:** Stat
- **Threshold:** Green < 50, Yellow < 100, Red ≥ 100

#### Panel 1.4 — Regression Rate (Gauge)
```promql
rate(l11_regressions_total[7d]) /
  rate(l11_findings_total[7d]) * 100
```
- **Type:** Gauge
- **Threshold:** Green < 10%, Red ≥ 25%

---

### Row 2: Severity Distribution

#### Panel 2.1 — Open Findings by Severity (Bar Chart)
```promql
l11_debt_open_total
```
- **Type:** Bar chart (grouped by severity label)
- **Colors:** P0=Red, P1=Orange, P2=Yellow, P3=Blue

#### Panel 2.2 — Findings by Tool (Pie Chart)
```promql
sum by (tool) (l11_findings_total)
```
- **Type:** Pie chart

#### Panel 2.3 — Mean Time to Remediation (Stat)
```promql
histogram_quantile(0.50, l11_remediation_duration_days_bucket)
```
- **Type:** Stat (in days)
- **Threshold:** Green < 7d, Yellow < 14d, Red ≥ 14d

---

### Row 3: Pipeline Performance

#### Panel 3.1 — Deterministic Scan Latency (Histogram)
```promql
histogram_quantile(0.95, l11_deterministic_scan_duration_ms_bucket)
```
- **Type:** Time series
- **Threshold:** Warn > 10s, Critical > 30s

#### Panel 3.2 — AI Enrichment Latency (Histogram)
```promql
histogram_quantile(0.95, l11_ai_enrichment_duration_ms_bucket)
```
- **Type:** Time series

#### Panel 3.3 — Circuit Breaker State (State Timeline)
```promql
l11_circuit_breaker_state
```
- **Type:** State timeline
- **Mapping:** 0=Closed (Green), 1=Half-Open (Yellow), 2=Open (Red)

#### Panel 3.4 — Auto-Fix Outcomes (Bar Chart)
```promql
sum by (outcome) (rate(l11_autofix_attempts_total[7d]))
```
- **Type:** Stacked bar chart

---

### Row 4: Cost Tracking

#### Panel 4.1 — Monthly AI Spend (Stat)
```promql
l11_ai_estimated_cost_usd
```
- **Type:** Stat (USD)
- **Threshold:** Green < $50, Yellow < $80, Red ≥ $100

#### Panel 4.2 — API Calls This Month (Counter)
```promql
increase(l11_ai_api_calls_total[30d])
```
- **Type:** Stat

#### Panel 4.3 — Budget Burn Rate (Time Series)
```promql
l11_ai_estimated_cost_usd / day_of_month() * days_in_month()
```
- **Type:** Time series (projected monthly spend)

---

## 3. Alert Rules

```yaml
# Grafana Alert Rules

groups:
  - name: l11-debt-alerts
    rules:

      - alert: L11_P0_Finding_Open
        expr: l11_debt_open_total{severity="P0"} > 0
        for: 1h
        labels:
          severity: critical
        annotations:
          summary: "L11: P0 debt finding open"
          description: "{{ $value }} P0 findings require immediate attention"

      - alert: L11_Debt_Ratio_High
        expr: l11_debt_ratio{scope="core"} > 10
        for: 24h
        labels:
          severity: warning
        annotations:
          summary: "L11: Core debt ratio > 10%"

      - alert: L11_Circuit_Breaker_Open
        expr: l11_circuit_breaker_state == 2
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "L11: AI circuit breaker is open"
          description: "AI enrichment disabled. Falling back to deterministic-only."

      - alert: L11_AI_Budget_Exceeded
        expr: l11_ai_estimated_cost_usd > 100
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "L11: Monthly AI budget exceeded ($100)"

      - alert: L11_Regression_Spike
        expr: rate(l11_regressions_total[1d]) > 5
        for: 6h
        labels:
          severity: warning
        annotations:
          summary: "L11: Regression rate spiking (>5/day)"

      - alert: L11_Deterministic_Slow
        expr: histogram_quantile(0.95, l11_deterministic_scan_duration_ms_bucket) > 30000
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "L11: Deterministic scan P95 > 30s"
```

---

## 4. Grafana Provisioning

```yaml
# grafana/provisioning/dashboards/l11.yaml
apiVersion: 1

providers:
  - name: L11 Debt Governance
    orgId: 1
    folder: L9-Governance
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    options:
      path: /var/lib/grafana/dashboards/l11
      foldersFromFilesStructure: true
```

---

## 5. Quick Queries for Debugging

### Neo4j: Top 10 open findings by risk score
```cypher
MATCH (f:Finding)
WHERE f.status IN ['open', 'regressed']
RETURN f.file, f.message, f.severity, f.risk_score
ORDER BY f.risk_score DESC
LIMIT 10
```

### Neo4j: Debt aging report
```cypher
MATCH (f:Finding)
WHERE f.status = 'open'
RETURN f.severity,
       avg(duration.between(f.first_seen, datetime()).days) AS avg_age_days,
       count(f) AS count
ORDER BY f.severity
```

### Prometheus: Debt half-life (days for 50% reduction)
```promql
# Manual calculation:
# half_life = -30 / log2(current_debt / debt_30_days_ago)
```
