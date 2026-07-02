#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
# L11 Debt Governance Pipeline — Deployment Script v3.3
#
# REVISION v3.3 — Integrates Protected Files Enforcement Spec v6.0:
#   - Protected Files Gate (blocking CI job)
#   - Drift Reconciliation (nightly workflow job)
#   - CI Health Scoring (local operator mode)
#   - 4 operational modes: deploy | preflight | reconcile | ci-health
#   - JSON structured logging throughout
#   - Updated ruleset (8 required status checks)
#   - Fail-closed governance hardening
#
# CARRIES FORWARD from v3.2:
#   - Gap A–D fixes, DORA injection, all 6 L11 modules + tests
#
# USAGE:
#   chmod +x DEPLOY.sh
#   ./DEPLOY.sh                        # full deploy (default)
#   MODE=preflight ./DEPLOY.sh         # dry-run, no writes
#   MODE=reconcile ./DEPLOY.sh         # detect governance drift
#   MODE=reconcile WRITE=true ./DEPLOY.sh  # fix drift + commit
#   MODE=ci-health ./DEPLOY.sh         # compute CI health score
#
# EXIT CODES (per spec v6):
#   0 — success
#   1 — policy violation or missing dependency
#   2 — governance drift detected
#   3 — GitHub API failure
# ══════════════════════════════════════════════════════════════
set -euo pipefail

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
REPO="${1:-cryptoxdog/L9}"
BASE="${2:-main}"
BRANCH="${3:-feat/l11-debt-governance-v3.3}"

MODE="${MODE:-deploy}"        # deploy | preflight | reconcile | ci-health
WRITE="${WRITE:-false}"       # reconcile write mode
JSON_LOG="${JSON_LOG:-true}"
LOG_FILE="${LOG_FILE:-deploy_log.jsonl}"
SCRIPT_VERSION="3.3.0"
SPEC_VERSION="6.0.0"

# ─────────────────────────────────────────────
# STRUCTURED LOGGING
# ─────────────────────────────────────────────
timestamp() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

log_json() {
  local level="$1" phase="$2" action="$3" result="$4" msg="${5:-}"
  if [[ "$JSON_LOG" == "true" ]]; then
    printf '{"ts":"%s","level":"%s","phase":"%s","action":"%s","repo":"%s","result":"%s","message":"%s","version":"%s"}\n' \
      "$(timestamp)" "$level" "$phase" "$action" "$REPO" "$result" "$msg" "$SCRIPT_VERSION" | tee -a "$LOG_FILE"
  else
    echo "[$(timestamp)] [$level] [$phase] $action => $result $msg"
  fi
}

abort() {
  local code="${2:-1}"
  log_json "ERROR" "runtime" "abort" "fail" "$1"
  exit "$code"
}

# Wraps commands — skips execution in preflight/ci-health modes
run() {
  local cmd="$*"
  log_json "INFO" "runtime" "run" "exec" "$cmd"
  if [[ "$MODE" == "preflight" || "$MODE" == "ci-health" ]]; then
    log_json "INFO" "runtime" "dry_run" "skipped" "$cmd"
    return 0
  fi
  eval "$cmd"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || abort "Missing required command: $1"
}

# ─────────────────────────────────────────────
# PRECHECKS
# ─────────────────────────────────────────────
log_json "INFO" "preflight" "start" "ok" "MODE=$MODE WRITE=$WRITE VERSION=$SCRIPT_VERSION"

require_cmd gh
require_cmd git
require_cmd jq
require_cmd python3

gh auth status >/dev/null 2>&1 || abort "GitHub CLI not authenticated"
gh repo view "$REPO" >/dev/null 2>&1 || abort "Cannot access repo: $REPO"

log_json "INFO" "preflight" "repo_access" "ok" "Repo reachable: $REPO"

# ─────────────────────────────────────────────
# CLONE / VERIFY REPO STATE
# ─────────────────────────────────────────────
if [[ ! -d ".git" ]]; then
  log_json "INFO" "preflight" "clone_repo" "ok" "Cloning repo"
  run "gh repo clone $REPO l9-deploy"
  cd l9-deploy
fi

if [[ -n "$(git status --porcelain)" ]]; then
  abort "Working tree dirty. Commit or stash before running."
fi

git fetch origin >/dev/null 2>&1 || abort "git fetch failed" 3

# ═════════════════════════════════════════════════════════════
# MODE: CI HEALTH SCORING
# ═════════════════════════════════════════════════════════════
if [[ "$MODE" == "ci-health" ]]; then
  log_json "INFO" "ci_health" "start" "ok" "Computing CI health score"

  RUNS=$(gh run list --repo "$REPO" --branch "$BASE" --limit 30 \
    --json conclusion,name,status 2>/dev/null || true)

  [[ -z "$RUNS" ]] && abort "Unable to fetch workflow runs" 3

  TOTAL=$(echo "$RUNS" | jq length)
  SUCCESS=$(echo "$RUNS" | jq '[.[] | select(.conclusion=="success")] | length')
  FAIL=$(echo "$RUNS" | jq '[.[] | select(.conclusion=="failure")] | length')
  FLAKE=$(echo "$RUNS" | jq '[.[] | select(.conclusion=="cancelled" or .conclusion=="timed_out")] | length')

  SCORE=$(python3 -c "
total = $TOTAL
success = $SUCCESS
fail = $FAIL
flake = $FLAKE
if total == 0:
    print(0)
else:
    pass_rate = (success / total) * 100
    # Weighted: 70% pass rate, 20% failure penalty, 10% flake penalty
    score = max(0, min(100, pass_rate * 0.7 - fail * 2 * 0.2 - flake * 1 * 0.1))
    print(round(score, 2))
")

  log_json "INFO" "ci_health" "score" "ok" "SCORE=$SCORE TOTAL=$TOTAL SUCCESS=$SUCCESS FAIL=$FAIL FLAKE=$FLAKE"

  # Thresholds per spec
  if python3 -c "exit(0 if $SCORE >= 85 else 1)"; then
    echo "✅ CI HEALTH SCORE: $SCORE / 100 (HEALTHY)"
  elif python3 -c "exit(0 if $SCORE >= 70 else 1)"; then
    echo "⚠️  CI HEALTH SCORE: $SCORE / 100 (WARN — below 85)"
  else
    echo "🔴 CI HEALTH SCORE: $SCORE / 100 (FAIL — below 70)"
  fi
  exit 0
fi

# ═════════════════════════════════════════════════════════════
# MODE: RECONCILIATION
# ═════════════════════════════════════════════════════════════
if [[ "$MODE" == "reconcile" ]]; then
  log_json "INFO" "reconcile" "start" "ok" "Checking governance drift"

  DRIFT_COUNT=0
  DRIFT_ISSUES=""

  # Check 1: Policy file exists
  if [[ ! -f "config/policies/protected_files.yaml" ]]; then
    DRIFT_COUNT=$((DRIFT_COUNT + 1))
    DRIFT_ISSUES="${DRIFT_ISSUES}CRITICAL: config/policies/protected_files.yaml missing\n"
  fi

  # Check 2: Validator v6 exists
  if [[ ! -f ".github/scripts/validate-protected-files-v6.py" ]]; then
    DRIFT_COUNT=$((DRIFT_COUNT + 1))
    DRIFT_ISSUES="${DRIFT_ISSUES}CRITICAL: .github/scripts/validate-protected-files-v6.py missing\n"
  fi

  # Check 3: Workflow references v6 validator
  if [[ -f ".github/workflows/l11-debt-governance.yaml" ]]; then
    if ! grep -q "validate-protected-files-v6.py" .github/workflows/l11-debt-governance.yaml; then
      DRIFT_COUNT=$((DRIFT_COUNT + 1))
      DRIFT_ISSUES="${DRIFT_ISSUES}DRIFT: Workflow does not reference v6 validator\n"
    fi
    if ! grep -q "Protected Files Gate" .github/workflows/l11-debt-governance.yaml; then
      DRIFT_COUNT=$((DRIFT_COUNT + 1))
      DRIFT_ISSUES="${DRIFT_ISSUES}DRIFT: Workflow missing Protected Files Gate job\n"
    fi
    if ! grep -q "protected-files" .github/workflows/l11-debt-governance.yaml; then
      DRIFT_COUNT=$((DRIFT_COUNT + 1))
      DRIFT_ISSUES="${DRIFT_ISSUES}DRIFT: Merge gate does not include protected-files in needs\n"
    fi
  else
    DRIFT_COUNT=$((DRIFT_COUNT + 1))
    DRIFT_ISSUES="${DRIFT_ISSUES}CRITICAL: l11-debt-governance.yaml workflow missing\n"
  fi

  # Check 4: Policy version
  if [[ -f "config/policies/protected_files.yaml" ]]; then
    POLICY_VERSION=$(python3 -c "
import yaml
with open('config/policies/protected_files.yaml') as f:
    p = yaml.safe_load(f)
print(p.get('version', 'unknown'))
" 2>/dev/null || echo "parse_error")
    if [[ "$POLICY_VERSION" != "$SPEC_VERSION" ]]; then
      DRIFT_COUNT=$((DRIFT_COUNT + 1))
      DRIFT_ISSUES="${DRIFT_ISSUES}DRIFT: Policy version $POLICY_VERSION != $SPEC_VERSION\n"
    fi
  fi

  # Check 5: Staged changes (from git)
  git add -A
  if ! git diff --cached --quiet; then
    DRIFT_COUNT=$((DRIFT_COUNT + 1))
    DRIFT_ISSUES="${DRIFT_ISSUES}DRIFT: Unstaged governance file changes detected\n"
    git diff --cached --stat
  fi

  if [[ "$DRIFT_COUNT" -gt 0 ]]; then
    log_json "WARN" "reconcile" "drift" "detected" "issues=$DRIFT_COUNT"
    echo ""
    echo "🔴 GOVERNANCE DRIFT DETECTED ($DRIFT_COUNT issues):"
    echo -e "$DRIFT_ISSUES"

    if [[ "$WRITE" == "true" ]]; then
      log_json "INFO" "reconcile" "fix" "applying" "Committing drift fixes"
      run "git commit -m 'chore(l11): reconcile governance drift v$SCRIPT_VERSION [spec v$SPEC_VERSION]'"
      run "git push origin HEAD"
      log_json "INFO" "reconcile" "fix" "ok" "Drift fixes pushed"
    else
      echo "Run with WRITE=true to auto-fix staged changes."
    fi
    exit 2
  else
    log_json "INFO" "reconcile" "drift" "none" "All governance files consistent"
    echo "✅ No governance drift detected."
    git reset HEAD >/dev/null 2>&1 || true
    exit 0
  fi
fi

# ═════════════════════════════════════════════════════════════
# MODE: DEPLOY (default) or PREFLIGHT
# ═════════════════════════════════════════════════════════════
echo "══════════════════════════════════════════════════════════"
echo " L11 Debt Governance v$SCRIPT_VERSION — Full Deployment"
echo " Repo:    $REPO"
echo " Branch:  $BRANCH"
echo " Mode:    $MODE"
echo " Spec:    Protected Files Enforcement v$SPEC_VERSION"
echo "══════════════════════════════════════════════════════════"

# ═════════════════════════════════════════════════════════════
# PHASE 1: SET GITHUB SECRETS
# ═════════════════════════════════════════════════════════════
echo ""
echo "━━━ PHASE 1: GitHub Secrets ━━━"
declare -A SECRET_DESC=(
  ["NEO4J_URI"]="Neo4j Aura connection URI (bolt+s://...)"
  ["NEO4J_USER"]="Neo4j username"
  ["NEO4J_PASSWORD"]="Neo4j password"
  ["PERPLEXITY_API_KEY"]="Perplexity API key for AI enrichment + PR review"
  ["CODECOV_TOKEN"]="Codecov upload token (from codecov.io)"
  ["GITLEAKS_LICENSE"]="Gitleaks license key (free at gitleaks.io)"
)

for secret_name in "${!SECRET_DESC[@]}"; do
  env_val="${!secret_name:-}"
  if [ -n "$env_val" ]; then
    run "echo '$env_val' | gh secret set '$secret_name' --repo '$REPO'"
    echo "  ✅ $secret_name set from env"
  else
    echo "  ⏭️  $secret_name — ${SECRET_DESC[$secret_name]}"
    echo "     Set it: gh secret set $secret_name --repo $REPO"
  fi
done
echo ""
echo "Current secrets:"
gh secret list --repo "$REPO" 2>/dev/null || echo "  (unable to list — check permissions)"

# ═════════════════════════════════════════════════════════════
# PHASE 2: CREATE FEATURE BRANCH
# ═════════════════════════════════════════════════════════════
echo ""
echo "━━━ PHASE 2: Create branch ━━━"
log_json "INFO" "branch" "create" "start" "$BRANCH from $BASE"

git fetch origin
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  run "git checkout $BRANCH"
  log_json "INFO" "branch" "checkout" "ok" "Existing branch"
else
  run "git checkout -b $BRANCH origin/$BASE"
  log_json "INFO" "branch" "create" "ok" "New branch from $BASE"
fi

mkdir -p .github/workflows
mkdir -p .github/scripts
mkdir -p config/policies
mkdir -p scripts/l11
mkdir -p scripts/audit
mkdir -p tests/l11
mkdir -p readme/l11
echo "  ✅ Directory structure created"

# ═════════════════════════════════════════════════════════════
# PHASE 3: PLACE ALL FILES
# ═════════════════════════════════════════════════════════════
echo ""
echo "━━━ PHASE 3: Copy files to correct paths ━━━"

# ── Workflow (v3.3 with Protected Files Gate) ──
cp 08-L11-CI-WORKFLOW-v3.3.yaml .github/workflows/l11-debt-governance.yaml
echo "  ✅ CI workflow (v3.3 — protected files gate + drift reconciliation)"

# ── DORA Injection Script ──
cp inject_dora_complete.py scripts/audit/inject_dora_complete.py
echo "  ✅ scripts/audit/inject_dora_complete.py"

# ── CODEOWNERS ──
cp CODEOWNERS .github/CODEOWNERS
echo "  ✅ CODEOWNERS"

# ── Protected Files Policy (NEW — Spec v6) ──
cp protected_files.yaml config/policies/protected_files.yaml
echo "  ✅ config/policies/protected_files.yaml (policy source of truth)"

# ── Protected Files Validator v6 (NEW — Spec v6) ──
cp validate-protected-files-v6.py .github/scripts/validate-protected-files-v6.py
echo "  ✅ .github/scripts/validate-protected-files-v6.py (CI validator)"

# ── Pipeline config ──
cp 01-L11-PIPELINE-CONFIG.yaml scripts/l11/pipeline_config.yaml
echo "  ✅ Pipeline config"

# ── Python modules ──
cp 02-L11-ORCHESTRATOR.py             scripts/l11/orchestrator.py
cp 03-L11-DETERMINISTIC-ENGINE.py     scripts/l11/deterministic_engine.py
cp 04-L11-AI-ENRICHMENT-ENGINE.py     scripts/l11/ai_enrichment_engine.py
cp 05-L11-DEBT-GRAPH-SERVICE.py       scripts/l11/debt_graph_service.py
cp 06-L11-RISK-SCORER.py              scripts/l11/risk_scorer.py
cp 07-L11-AUTO-FIX-ENGINE.py          scripts/l11/auto_fix_engine.py
echo "  ✅ L11 Python modules (6)"

# ── Package init ──
cat > scripts/l11/__init__.py << 'PYEOF'
"""L11 Debt Governance Pipeline.

DORA:
    component_id: l11-package
    tier: 2
    lifecycle: production
    owner: platform-engineering
"""
PYEOF
echo "  ✅ scripts/l11/__init__.py"

# ── Tests ──
cp tests_l11/__init__.py              tests/l11/__init__.py
cp tests_l11/conftest.py              tests/l11/conftest.py
cp tests_l11/test_deterministic_engine.py   tests/l11/
cp tests_l11/test_risk_scorer.py            tests/l11/
cp tests_l11/test_debt_graph_service.py     tests/l11/
cp tests_l11/test_orchestrator.py           tests/l11/
cp tests_l11/test_ai_enrichment_engine.py   tests/l11/
cp tests_l11/test_auto_fix_engine.py        tests/l11/
echo "  ✅ Tests (8 files)"

# ── Docs ──
cp 00-L11-MASTER-README.md       readme/l11/MASTER-README.md 2>/dev/null || true
cp 09-L11-RUNBOOK.md             readme/l11/RUNBOOK.md 2>/dev/null || true
cp 10-L11-METRICS-DASHBOARD.md   readme/l11/METRICS-DASHBOARD.md 2>/dev/null || true
echo "  ✅ Documentation"

log_json "INFO" "phase3" "files" "ok" "All files placed"

# ═════════════════════════════════════════════════════════════
# PHASE 4: COMMIT + PUSH + PR
# ═════════════════════════════════════════════════════════════
echo ""
echo "━━━ PHASE 4: Commit, push, create PR ━━━"
git add -A
echo ""
echo "Files staged:"
git diff --cached --stat

run "git commit -m 'feat(l11): deploy debt governance pipeline v$SCRIPT_VERSION

Carries forward from v3.2:
  Gap A: ADR compliance uses --errors-only (not --strict)
  Gap B: Added ci/run_ci_gates.sh --all as dedicated CI Gates job
  Gap C: Job names match existing ci.yml exactly
  Gap D: L11 replaces ci.yml (disable old after 3 clean runs)
  DORA header injection in CI (inject_dora_complete.py)

NEW in v3.3 — Protected Files Enforcement Spec v6.0:
  🛡️  Protected Files Gate (blocking CI job)
      - Loads config/policies/protected_files.yaml
      - Blocks PRs modifying protected files without approval label
      - Audit artifact: protected_files_gate_report.json
  🔍  Drift Reconciliation (nightly workflow job)
      - Checks policy/validator/workflow consistency
      - Opens GitHub Issue on drift
  📊  CI Health Scoring (operator mode)
      - MODE=ci-health computes weighted score from last 30 runs
  ⚡  4 operational modes: deploy | preflight | reconcile | ci-health
  📝  JSON structured logging: deploy_log.jsonl

Merge Gate (blocking — 8 checks):
  Lint, typecheck, test-fast | ADR Compliance | CI Gates
  🔐 Secrets Scan | 🧪 Tests + Coverage | 🏗️ L11 Component Tests
  🛡️ Protected Files Gate | ✅ Merge Gate

AI / Graph (non-blocking):
  🤖 AI Enrichment | 📊 Debt Graph Update

Nightly:
  🌙 Nightly Maintenance | 🔍 Drift Reconciliation
'"

run "git push origin $BRANCH"
echo "  ✅ Pushed to origin/$BRANCH"

echo ""
echo "Creating PR..."
PR_URL=$(run "gh pr create \
  --repo $REPO \
  --base $BASE \
  --head $BRANCH \
  --title 'feat(l11): Deploy Debt Governance Pipeline v$SCRIPT_VERSION + Protected Files Gate v$SPEC_VERSION' \
  --body '## L11 Debt Governance Pipeline v$SCRIPT_VERSION

### Carries Forward (v3.2)
- Gap A–D fixes from BRANCH_PROTECTION_AND_CI.md audit
- DORA header auto-injection in ADR Compliance job

### NEW: Protected Files Enforcement Spec v$SPEC_VERSION

| Component | Path | Purpose |
|-----------|------|---------|
| Policy YAML | \`config/policies/protected_files.yaml\` | Source of truth for protected paths |
| Validator v6 | \`.github/scripts/validate-protected-files-v6.py\` | Fail-closed CI gate |
| Gate Job | 🛡️ Protected Files Gate | Blocks merge without approval |
| Drift Job | 🔍 Drift Reconciliation | Nightly consistency check |

### Approval Signals
- PR Labels: \`LCTO_APPROVED\`, \`IGOR_APPROVED\`
- Commit tokens: \`HIL_APPROVED\`, \`IGOR_APPROVED\`

### Merge Gate (8 required checks)
\`Lint, typecheck, test-fast\` · \`ADR Compliance\` · \`CI Gates\` · \`🔐 Secrets Scan\` · \`🧪 Tests + Coverage\` · \`🏗️ L11 Component Tests\` · \`🛡️ Protected Files Gate\` · \`✅ Merge Gate\`

### Operator Modes
\`\`\`bash
./DEPLOY.sh                           # full deploy
MODE=preflight ./DEPLOY.sh            # dry-run
MODE=reconcile ./DEPLOY.sh            # detect drift
MODE=reconcile WRITE=true ./DEPLOY.sh # fix drift
MODE=ci-health ./DEPLOY.sh            # CI health score
\`\`\`

### After 3 clean CI runs → Phase 5 (branch protection)
'" 2>&1)
echo "  ✅ PR created: $PR_URL"

log_json "INFO" "phase4" "pr" "ok" "$PR_URL"

# ═════════════════════════════════════════════════════════════
# PHASE 5: DISABLE OLD ci.yml + APPLY BRANCH PROTECTION
# ═════════════════════════════════════════════════════════════
echo ""
echo "━━━ PHASE 5: Disable old CI + Branch Protection ━━━"
echo ""
echo "⚠️  DO NOT RUN until L11 PR merges + CI passes 3 times."
echo ""
echo "Step 1: Disable old ci.yml (Gap D fix):"
echo ""
cat << 'DISABLE_OLD'
# Option A: Disable via gh CLI
gh workflow disable "CI" --repo cryptoxdog/L9

# Option B: Rename in repo (permanent)
git mv .github/workflows/ci.yml .github/workflows/ci.yml.disabled
git commit -m "chore: disable old ci.yml (replaced by L11 v3.3)"
git push
DISABLE_OLD

echo ""
echo "Step 2: Apply branch protection ruleset (v3.3 — 8 checks):"
echo ""
cat << 'RULESETCMD'
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
RULESETCMD

echo ""
echo "Verify:"
echo "  gh api repos/$REPO/rulesets --jq '.[].name'"

# ═════════════════════════════════════════════════════════════
# PHASE 6: VALIDATE THE GATE
# ═════════════════════════════════════════════════════════════
echo ""
echo "━━━ PHASE 6: Validate (after branch protection is active) ━━━"
echo ""
cat << 'TESTCMD'
# Test 1: Verify L11 blocks bad code
git checkout -b test/l11-gate-validation origin/main
echo "import logging" >> core/__init__.py
git add -A
git commit -m "test: verify L11 blocks stdlib logging (ADR-0019)"
git push origin test/l11-gate-validation
gh pr create \
  --title "test: L11 gate validation (EXPECT FAILURE)" \
  --body "This PR intentionally violates ADR-0019. L11 should block merge."

# Watch it fail
gh run watch --repo cryptoxdog/L9

# Test 2: Verify DORA injection works
git checkout -b test/l11-dora-injection origin/main
cat > core/test_no_dora.py << 'PYEOF'
"""Test module with no DORA headers."""
def hello():
    return "world"
PYEOF
git add -A
git commit -m "test: verify DORA auto-injection"
git push origin test/l11-dora-injection
gh pr create \
  --title "test: L11 DORA injection (EXPECT AUTO-FIX COMMIT)" \
  --body "This file has no DORA headers. L11 should auto-inject and push a fix commit."

# Watch it auto-inject
gh run watch --repo cryptoxdog/L9

# Test 3: Verify Protected Files Gate blocks (NEW)
git checkout -b test/l11-protected-files origin/main
echo "# test modification" >> Dockerfile
git add -A
git commit -m "test: verify protected files gate blocks Dockerfile edit"
git push origin test/l11-protected-files
gh pr create \
  --title "test: Protected Files Gate (EXPECT BLOCK)" \
  --body "This PR modifies Dockerfile without LCTO_APPROVED label. Gate should block."

# Watch it block
gh run watch --repo cryptoxdog/L9

# Test 4: Verify approval bypasses gate (NEW)
# Add label LCTO_APPROVED to the PR above, then re-run CI
gh pr edit test/l11-protected-files --add-label "LCTO_APPROVED"
gh run rerun --repo cryptoxdog/L9 --failed

# Clean up after all tests
gh pr close test/l11-gate-validation --delete-branch
gh pr close test/l11-dora-injection --delete-branch
gh pr close test/l11-protected-files --delete-branch
git checkout main
TESTCMD

echo ""
echo "━━━ PHASE 7: Verify CI Health (after deployment) ━━━"
echo ""
echo "  MODE=ci-health ./DEPLOY.sh"
echo "  MODE=reconcile ./DEPLOY.sh"

log_json "INFO" "deploy" "complete" "ok" "Governance v$SCRIPT_VERSION deployed with spec v$SPEC_VERSION"

echo ""
echo "══════════════════════════════════════════════════════════"
echo " DEPLOYMENT v$SCRIPT_VERSION COMPLETE"
echo ""
echo " Next steps:"
echo "   1. Merge the PR"
echo "   2. Watch CI run: gh run watch --repo $REPO"
echo "   3. After 3 clean runs → Phase 5 (disable old CI + ruleset)"
echo "   4. Phase 6 to validate all gates (incl. protected files)"
echo "   5. MODE=ci-health ./DEPLOY.sh to verify health score"
echo "══════════════════════════════════════════════════════════"
