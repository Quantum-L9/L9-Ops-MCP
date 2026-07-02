# --- L9_META ---
# l9_schema: 1
# artifact_type: build_contract
# tags: pr-repair, makefile, cli
# retrieval: on_demand
# status: active
# --- /L9_META ---

.PHONY: pr-fix pr-fix-dry pr-fix-propose pr-fix-verify pr-fix-learn

pr-fix:
	python -m pr_repair.cli run --mode repair_and_verify

pr-fix-dry:
	python -m pr_repair.cli run --mode dry_run

pr-fix-propose:
	python -m pr_repair.cli run --mode propose_only

pr-fix-verify:
	python -m pr_repair.cli verify

pr-fix-learn:
	python -m pr_repair.cli learn
