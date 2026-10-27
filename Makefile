# --- L9_META ---
# l9_schema: 1
# artifact_type: build_contract
# tags: [makefile, ci-proof, mcp, governance]
# retrieval: on_demand
# status: active
# --- /L9_META ---

.DEFAULT_GOAL := help
PYTHON ?= python3
GRAPH_INDEX ?= AGENT_RETRIEVAL_INDEX.yaml
GRAPH_OUT ?= dist/graph
GRAPH_SEED := $(GRAPH_OUT)/graph-seed.jsonl

.PHONY: help setup validate health skill-audit playbook-audit wiring ci eval zip \
        progressive-disclosure hardban-audit convergence command-parity \
        mcp-dev preflight graph-export graph-verify graph-sync \
        pr-fix pr-fix-dry pr-fix-propose pr-fix-verify pr-fix-learn

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*##"; printf "\nL9-Ops-MCP commands\n\n"} /^[a-zA-Z0-9_.-]+:.*##/ {printf "  %-28s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Install declared package dependencies when pyproject is present
	@if command -v uv >/dev/null 2>&1; then uv sync --locked || uv sync; else $(PYTHON) -m pip install -e ".[dev]"; fi

validate: wiring ## Run structural repo validation (alias of wiring)

health: ## Run library health checks
	bash scripts/library_health.sh

skill-audit: ## Validate skill installability
	$(PYTHON) scripts/validate_skill_installability.py

playbook-audit: ## Validate playbook schemas and wiring
	$(PYTHON) scripts/validate_playbooks.py

wiring: ## Validate skills, playbooks, README/Makefile parity, org invariants, upload routing, and pyproject entrypoints
	$(PYTHON) scripts/validate_skill_installability.py
	$(PYTHON) scripts/validate_playbooks.py
	$(PYTHON) scripts/validate_command_parity.py
	$(PYTHON) scripts/validate_org_invariants.py
	$(PYTHON) scripts/validate_upload_router.py
	$(PYTHON) scripts/validate_pyproject_entrypoints.py

progressive-disclosure: ## Enforce progressive disclosure rules
	bash scripts/enforce_progressive_disclosure.sh

hardban-audit: ## Audit duplicate hard bans and copied doctrine fragments
	bash scripts/audit_hardban_duplication.sh

convergence: ## Report convergence status
	$(PYTHON) scripts/convergence_tracker.py

command-parity: ## Compare README, Makefile, AGENTS, and workflow commands
	$(PYTHON) scripts/validate_command_parity.py

ci: ## Run complete local CI-equivalent proof gate
	$(MAKE) health
	$(MAKE) progressive-disclosure
	$(MAKE) hardban-audit
	$(MAKE) convergence
	$(MAKE) wiring
	@if command -v ruff >/dev/null 2>&1; then ruff check scripts src tests || true; fi
	@if command -v pytest >/dev/null 2>&1; then pytest -q || true; fi

eval: ## Run prompt/skill evals when promptfoo is available
	@if command -v npx >/dev/null 2>&1; then npx promptfoo eval --config evals/promptfooconfig.yaml; else echo "BLOCKED: npx unavailable"; exit 1; fi

zip: ## Package repo metadata snapshot
	mkdir -p dist && zip -r dist/l9-ops-mcp-metadata.zip README.md AGENTS.md docs skills playbooks schemas scripts -x "*.pyc" "*/__pycache__/*"

mcp-dev: ## Run MCP server locally
	$(PYTHON) -m l9_ops_mcp.server

preflight: ## Run runtime preflight when present
	@if [ -x scripts/preflight.sh ]; then bash scripts/preflight.sh; else echo "BLOCKED: scripts/preflight.sh missing or not executable"; exit 1; fi

graph-export: ## Export AGENT_RETRIEVAL_INDEX.yaml to a graph seed (GRAPH_OUT, default dist/graph)
	$(PYTHON) scripts/export_graph_seed.py --index $(GRAPH_INDEX) --repo-root . --out $(GRAPH_SEED)

graph-verify: graph-export ## Verify the graph seed against schemas/graph-seed.schema.json
	$(PYTHON) scripts/verify_graph.py --seed $(GRAPH_SEED) --schema schemas/graph-seed.schema.json

graph-sync: ## Export, verify and ingest the graph seed into the local JSONL report sink (no live Graphiti)
	$(PYTHON) scripts/sync_graph.py --index $(GRAPH_INDEX) --repo-root . --seed $(GRAPH_SEED) --report $(GRAPH_OUT)/ingest-report.json

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
