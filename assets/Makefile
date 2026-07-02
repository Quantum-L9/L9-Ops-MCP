# =============================================================================
# L9 IgorOS Pack — Makefile
# Automation for: harvest, validate, format-check, health, eval, and zip
# =============================================================================

PACK_VERSION := 3.4.0
PACK_ROOT    := $(shell pwd)

.PHONY: help validate health lint eval harvest zip clean

# Default target
help:
	@echo ""
	@echo "L9 IgorOS Pack v$(PACK_VERSION)"
	@echo ""
	@echo "  make harvest      — Check IgorOS source files against this pack (diff audit)"
	@echo "  make validate     — Validate all canonical headers on kernels and skills"
	@echo "  make health       — Run library health: stale evals, missing metadata, rot detection"
	@echo "  make lint         — Lint YAML files for syntax errors"
	@echo "  make eval         — Run Promptfoo eval suite against all skills"
	@echo "  make skill-audit  — Audit all custom skill endpoints (exits 1 on failure)"
	@echo "  make zip          — Bundle pack for deployment"
	@echo "  make clean        — Remove generated artifacts"
	@echo ""

# --------------------------------------------------------------------------
# HARVEST — Check IgorOS source alignment
# --------------------------------------------------------------------------
harvest:
	@echo "=== Harvest Audit: IgorOS sources vs Pack ==="
	@echo "Checking USER.md coverage..."
	@python3 scripts/harvest_audit.py --source docs/profiles/USER.md --check-fields title,purpose,summary,version,tags,retrieval_keys
	@echo "Checking soul_kernel coverage..."
	@python3 scripts/harvest_audit.py --source docs/kernels/R0/soul_kernel.v1.yaml --check-fields kernel_id,ring,core_laws,behavioral_mandates,hard_prohibitions,skill_first_law,memory_protocol,planner_invocation_law,model_routing,first_order_thinking
	@echo "Checking preferences_kernel coverage..."
	@python3 scripts/harvest_audit.py --source docs/kernels/R5/preferences_kernel.v1.yaml --check-fields kernel_id,interaction_style,context_management,deliverable_standards,governance
	@echo "Done."

# --------------------------------------------------------------------------
# VALIDATE — Canonical header enforcement
# --------------------------------------------------------------------------
validate:
	@echo "=== Canonical Header Validation ==="
	@python3 scripts/validate_headers.py --dir docs/kernels --ext .yaml --required title,purpose,summary,version,created,owner,tags,domain,type,production_ready,ring
	@python3 scripts/validate_headers.py --dir skills --ext .md --required title,purpose,summary,version,created,owner,tags,domain,type,production_ready,retrieval_keys,trigger_description
	@python3 scripts/validate_headers.py --dir docs/profiles --ext .md --required title,purpose,summary,version,created,owner,tags,domain,type,production_ready,retrieval_keys
	@echo "Validation complete."

# --------------------------------------------------------------------------
# HEALTH — Library health check
# --------------------------------------------------------------------------
health:
	@echo "=== Library Health Check ==="
	@python3 scripts/library_health.py \
		--stale-days 90 \
		--check-eval-coverage \
		--check-tier-markers \
		--check-missing-retrieval-keys \
		--report health_report.md
	@echo "Health report written to health_report.md"

# --------------------------------------------------------------------------
# LINT — YAML syntax check
# --------------------------------------------------------------------------
lint:
	@echo "=== YAML Lint ==="
	@find docs/kernels -name "*.yaml" -exec python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" {} \; && echo "All YAML valid"
	@find skills -name "*.yaml" -exec python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" {} \; && echo "All skill YAML valid"

# --------------------------------------------------------------------------
# EVAL — Promptfoo eval suite
# --------------------------------------------------------------------------
eval:
	@echo "=== Running Eval Suite ==="
	npx promptfoo eval --config evals/promptfooconfig.yaml --output evals/results/latest.json
	@echo "Results in evals/results/latest.json"

# --------------------------------------------------------------------------
# SKILL AUDIT — Custom skill endpoint health (exits 1 on failure)
# --------------------------------------------------------------------------
skill-audit:
	@echo "=== Custom Skill Endpoint Audit ==="
	@python3 scripts/skill_endpoint_audit.py --skills-dir skills --exit-on-failure
	@echo "All skill endpoints healthy."

# --------------------------------------------------------------------------
# ZIP — Bundle for deployment
# --------------------------------------------------------------------------
zip:
	@echo "=== Bundling Pack v$(PACK_VERSION) ==="
	@mkdir -p dist
	@zip -r dist/l9-igoros-pack-v$(PACK_VERSION).zip \
		AGENTS.md \
		Makefile \
		docs/ \
		skills/ \
		playbooks/ \
		schemas/ \
		scripts/ \
		evals/ \
		--exclude "*/dist/*" \
		--exclude "*/.git/*" \
		--exclude "*/__pycache__/*" \
		--exclude "*/node_modules/*"
	@echo "Pack bundled: dist/l9-igoros-pack-v$(PACK_VERSION).zip"

# --------------------------------------------------------------------------
# CLEAN
# --------------------------------------------------------------------------
clean:
	@rm -rf dist/ evals/results/ health_report.md
	@echo "Cleaned."

# --------------------------------------------------------------------------
# SHORTCUTS
# --------------------------------------------------------------------------
all: lint validate health
ci: lint validate eval
