<!-- L9_META
l9_schema: 1
origin: l9-kernel
layer: [agent-rules, kernel, build-quality]
tags: [L9_KERNEL, build-quality, artifact-review, no-stub, operator-readiness, harness]
owner: platform
status: active
canonical_path: docs/kernels/R5/l9_build_kernel.v1.md
version: 3.3.0
last_tested: "2026-06-17"
eval_status: pending
overload_weight: 1.5
ring: R5
load_condition: "artifact_review OR pack_validation OR release_prep OR handoff_pack OR generated_code_review OR build_quality"
requires: [l9_coding_kernel.v1]
amplifies: [agent_review_kernel.v1, eval_harness_kernel.v1]
single_source_rule: "NEVER copy this file. Reference by path only. One version. No forks."
/L9_META -->

## TIER 1 — CAPABILITY DECLARATION

**capability**: Enforces L9 artifact quality gates for execution artifacts, release packs,
generated repos, pipeline modules, validation bundles, and agent handoff packs.

**use_when**: Artifact review, pack validation, release preparation, handoff pack generation,
generated code review, or any build quality gate evaluation.

**do_not_use_when**: Pure code generation tasks where l9_coding_kernel is the sole active
kernel and no artifact review is in scope.

**core_laws**:
1. Execution depth beats folder neatness.
2. Full contracts beat compressed schemas.
3. Specific adapters beat generic replacement wrappers.
4. Real validation beats pass-only reports.
5. Real files beat placeholder directories.
6. Operator readiness is mandatory, not decorative.
7. A pack that cannot be used immediately is not execution-ready.

**hard_bans**:
- MUST NOT declare a pack execution-ready if any stub/placeholder/pass-only function exists
- MUST NOT ship compressed schemas that omit fields, constraints, or failure behavior
- MUST NOT use .gitkeep to satisfy any required artifact gate
- MUST NOT ship validation reports containing only `status: pass`
- MUST NOT treat folder organization as evidence of completeness
- MUST NOT copy this file into any other location — reference by canonical path only

---

## TIER 2 — OPERATIONAL RULES

# ============================================================================
# L9 BUILD KERNEL — EXECUTION ARTIFACT QUALITY ENFORCEMENT
# ============================================================================
# date: 2026-06-08 | status: supplemental_active_candidate
# Closes concrete artifact-quality gaps not covered by architecture, reasoning,
# convergence, or no-stub kernels.
# ============================================================================

## SCOPE

Applies to: generated_code_packs, release_bundles, repo_modules, pipeline_systems,
validation_artifacts, learning_systems, agent_handoff_packages.

**Load order**:
- After: zero_stub_build_protocol, developer_core_kernel, convergence_kernel
- Before: final_validation, release_packaging

---

## MODEL LAYER REQUIREMENTS

Structured internal entities MUST use a dataclass-style model layer (Python @dataclass,
Pydantic BaseModel, attrs, or equivalent typed declarative model) where pipeline state,
contracts, adapter payloads, validation records, or persistent artifacts are represented.

**Must include**: explicit_fields, type_annotations, defaults_where_safe,
serialization_boundary, validation hooks where needed.

**Must NOT**: use loose dicts as primary model layer, hide state in opaque objects,
collapse artifacts into undocumented blobs, use model classes without importable init.

---

## PACKAGE AND DATA REQUIREMENTS

- MUST include real `__init__.py` files wherever modules are imported
- MUST include real JSONL files (with documented schema + representative rows) when JSONL paths are in scope
- MUST NOT use `.gitkeep` to satisfy any required artifact/data/package gate
- `.gitkeep` MAY exist only for intentionally-empty optional directories

---

## ABSOLUTE NO-STUB POLICY

**Forbidden**: stubs, placeholders, TODO_only_implementations, pass_only_functions,
fake_outputs, fake_validation, dead_scaffolds, orphan_files, unreachable_modules,
unimplemented_interfaces, decorative_configs, empty_reports, mock_success_outputs.

**Enforcement**:
- Any incomplete area MUST be labeled Unknown, intentionally omitted, or blocked
- Any required but incomplete component MUST fail validation
- No generated pack may claim execution readiness while containing stubs

---

## MANDATORY PACK CONTENTS

### Contracts (required)
- Full contracts with complete schemas
- Required fields, optional fields, constraints, allowed values, failure behavior
- Versioning when contracts are public, persistent, or reused

### Manifest (required)
- Artifact inventory, dependency graph, execution graph, validation inventory
- Ownership/source mapping, timestamps, known limitations, Unknowns

### Pipeline Stage Logic (required)
- Each stage defines: inputs, outputs, transforms, side effects, errors, failure conditions
- Each stage inspectable and testable
- Stage collapsing forbidden unless justified and validated
- Logic compression that reduces observability forbidden

### Adapters (required)
- Specific adapters per real source/domain/interface
- Generic adapters as shared utilities only — MUST NOT replace explicit adapters
- Each adapter: accepted input shape, normalized output shape, error handling, unsupported cases

### Validation Reports (required)
- Executed checks, pass/fail counts, findings, evidence, remediation actions, unresolved risks
- MUST NOT consist solely of `status: pass`

### Improvement Reports (required)
- What changed, why, expected effect, residual gaps, next recommended improvement
- Distinguish cosmetic improvement from functional improvement

### Sink / Retrieval / Report Implementations (required)
- Write/read paths, formats, append behavior, idempotency, failure handling

---

## FORBIDDEN PACK PATTERNS

| Pattern | Rule |
|---|---|
| Compressed schemas | MUST NOT omit fields, constraints, examples, validation rules, or failure cases |
| Over-thinned pipeline modules | MUST NOT reduce to shallow pass-through wrappers or remove stage-level observability |
| Generic adapter replacement | MUST NOT replace specific adapters with generic wrappers |
| Empty validation | MUST NOT ship reports whose only evidence is success status |
| Cosmetic packaging | MUST NOT treat folder organization, file count, or naming polish as proof of quality |

---

## LARGE PACK OPERATOR READINESS (> 10 files)

Required files: `README.md`, `RUNBOOK.md`, `MANIFEST.md`, `VALIDATION.md`

### README.md
What this pack is / what problem it solves / what is included / what is not included /
folder-file map / core execution path / how to inspect / how to validate / how to extend.

### RUNBOOK.md
Instant setup / exact commands / required environment / expected outputs /
known failure modes / recovery steps / validation commands / agent-operator handoff instructions.

### MANIFEST.md
Complete file inventory / purpose of each major artifact / source mapping /
dependency map / execution map / validation map.

### VALIDATION.md
Validation methodology / checks run / results / known gaps / how to rerun.

---

## CLASSIFICATION POLICY

| Status | Criteria |
|---|---|
| `execution_ready` | All mandatory gates pass. No stubs. README/RUNBOOK/MANIFEST/VALIDATION present when required. Validation evidence-bearing. |
| `mine_for_components_only` | Useful components but fails one or more execution-readiness gates. |
| `reject_as_over_thinned` | Cleaner structure but materially weaker schemas, logic, adapters, or validation. |
| `blocked_on_operator_readiness` | Technically plausible but lacks docs/runbook/manifest for instant use. |
| `fail_execution_ready` | Any hard gate fails. |

---

## VALIDATION GATES

| Gate | Test |
|---|---|
| `dataclass_model_layer_present` | PASS only if structured models exist and are used |
| `real_package_initialization_present` | PASS only if importable package paths include real `__init__.py` |
| `real_jsonl_files_present_when_required` | PASS only if JSONL paths include real files with documented schema |
| `no_placeholder_substitution` | PASS only if `.gitkeep` does not satisfy any required gate |
| `zero_stubs_placeholders` | PASS only if zero stubs/placeholders/fake-validation exist |
| `full_contracts_present` | PASS only if contracts are complete and not compressed |
| `detailed_manifest_present` | PASS only if manifest includes inventory, graphs, source mapping, Unknowns |
| `full_pipeline_logic_present` | PASS only if stages expose inputs, outputs, transforms, errors, side effects, failure conditions |
| `specific_adapters_present` | PASS only if explicit adapters exist and generics do not replace them |
| `rich_validation_present` | PASS only if reports contain checks, evidence, findings, remediation, unresolved risks |
| `rich_improvement_present` | PASS only if reports contain functional deltas, rationale, effects, residual gaps, next actions |
| `sink_retrieval_report_implementations_present` | PASS only if sink, retrieval, and report implementations exist where in scope |
| `large_pack_docs_present` | PASS only if packs > 10 files include README, RUNBOOK, MANIFEST, VALIDATION |
| `instant_operator_use` | PASS only if developer/agent can inspect, run, validate, extend without follow-up questions |

---

## REVIEW PROCEDURE

1. Inventory actual files first
2. Normalize root paths before comparison
3. Classify artifacts by role
4. Inspect content, not filenames
5. Run stub/placeholder scan
6. Check importability and package initialization
7. Check data artifacts
8. Check schema completeness
9. Check pipeline depth
10. Check adapter specificity
11. Check validation evidence
12. Check operator docs
13. Classify pack status
14. Recommend: use / reject / mine-for-components only

---

## OUTPUT REQUIREMENTS FOR REVIEWS

Required sections in every review output:

1. `executive_decision` — binary classification + one-sentence rationale
2. `pack_status` — classification policy value
3. `hard_gate_results` — per-gate PASS/FAIL with evidence
4. `mandatory_contents_check` — each required artifact present/absent/deficient
5. `forbidden_patterns_check` — any forbidden patterns found
6. `operator_readiness_check` — README/RUNBOOK/MANIFEST/VALIDATION pass/fail
7. `defects` — specific, evidenced defects
8. `salvageable_components` — what is worth keeping if pack fails
9. `final_recommendation` — use / reject / mine-for-components
10. `smallest_next_action` — single lowest-effort fix to unblock execution-readiness
11. `unknowns` — what could not be determined from the artifact alone
12. `convergence_block` — whether this pack should block release
