# --- L9_META ---
# l9_schema: 1
# artifact_type: build_contract
# tags: [makefile, ci-proof, mcp, governance]
# retrieval: on_demand
# status: active
# --- /L9_META ---

# Repository implementation for Core's immutable make-v1 facade.
# Prefer the clean environment established by repo-setup; allow explicit override.
PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

.PHONY: repo-setup repo-validate repo-check repo-test repo-help health \
        skill-audit playbook-audit wiring ci eval zip progressive-disclosure \
        hardban-audit impact convergence command-parity mcp-dev preflight \
        graph-export graph-verify graph-sync pr-fix pr-fix-dry pr-fix-propose \
        pr-fix-verify pr-fix-learn test-fast

repo-setup: ## Install declared dependencies in a repository-local virtual environment
	python3 -m venv .venv
	.venv/bin/python -m pip install -e ".[dev]"

repo-validate: wiring command-parity ## Validate repository structure and command wiring

repo-check: health progressive-disclosure hardban-audit impact convergence ## Enforce static and governance checks
	$(PYTHON) -m ruff check src scripts tests
	$(PYTHON) -m mypy src/l9_ops_mcp

repo-test: ## Execute the complete product and L11 test suites; failures block CI
	$(PYTHON) -m pytest tests scripts -q

test-fast: ## Execute the existing non-slow product tests
	$(PYTHON) -m pytest tests -m "not slow" --tb=short -q

repo-help: ## Show repository-specific commands
	@awk 'BEGIN {FS = ":.*##"; printf "\nL9-Ops-MCP commands\n\n"} /^[a-zA-Z0-9_.-]+:.*##/ {printf "  %-28s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

health: ## Run library health checks
	bash scripts/library_health.sh

skill-audit: ## Validate skill installability
	$(PYTHON) scripts/validate_skill_installability.py

playbook-audit: ## Validate playbook schemas and wiring
	$(PYTHON) scripts/validate_playbooks.py

wiring: ## Validate AGENTS, workflows, Makefile, README, schemas, and pyproject entrypoints
	$(PYTHON) scripts/validate_wiring.py --all

progressive-disclosure: ## Enforce progressive disclosure rules
	bash scripts/enforce_progressive_disclosure.sh

hardban-audit: ## Audit duplicate hard bans and copied doctrine fragments
	bash scripts/audit_hardban_duplication.sh

impact: ## Analyze declared repository dependencies and their impact surface
	$(PYTHON) scripts/impact_analysis.py --all

convergence: ## Report convergence status
	$(PYTHON) scripts/convergence_tracker.py

command-parity: ## Compare README, Makefile includes, AGENTS, and workflow commands
	$(PYTHON) scripts/validate_command_parity.py

ci: ## Run the same fail-closed validate, check, and test phases as organization Core
	$(MAKE) validate
	$(MAKE) check
	$(MAKE) test

eval: ## Run prompt/skill evals when promptfoo is available
	@if command -v npx >/dev/null 2>&1; then npx promptfoo eval --config evals/promptfooconfig.yaml; else echo "BLOCKED: npx unavailable"; exit 1; fi

zip: ## Package repo metadata snapshot
	mkdir -p dist && zip -r dist/l9-ops-mcp-metadata.zip README.md AGENTS.md docs skills playbooks schemas scripts -x "*.pyc" "*/__pycache__/*"

mcp-dev: ## Run MCP server locally
	$(PYTHON) -m l9_ops_mcp.server

preflight: ## Run runtime preflight when present
	@if [ -x scripts/preflight.sh ]; then bash scripts/preflight.sh; else echo "BLOCKED: scripts/preflight.sh missing or not executable"; exit 1; fi

graph-export: ## Export artifact metadata to graph seed
	$(PYTHON) scripts/export_graph_seed.py --index ./out/meta/retrieval-index.json --manifest ./out/meta/artifact-manifest.json --out ./out/graph/graph-seed.jsonl

graph-verify: ## Verify graph seed schema
	$(PYTHON) scripts/verify_graph.py --seed ./out/graph/graph-seed.jsonl --schema schemas/graph-seed.schema.json

graph-sync: ## Sync graph seed to Graphiti
	$(PYTHON) scripts/sync_graph.py --seed ./out/graph/graph-seed.jsonl

pr-fix: ## Run PR repair workflow
	$(PYTHON) -m pr_repair.cli run --mode repair_and_verify

pr-fix-dry: ## Run PR repair in dry-run mode
	$(PYTHON) -m pr_repair.cli run --mode dry_run

pr-fix-propose: ## Propose PR repair only
	$(PYTHON) -m pr_repair.cli run --mode propose_only

pr-fix-verify: ## Verify PR repair outputs
	$(PYTHON) -m pr_repair.cli verify

pr-fix-learn: ## Learn from PR repair result
	$(PYTHON) -m pr_repair.cli learn
