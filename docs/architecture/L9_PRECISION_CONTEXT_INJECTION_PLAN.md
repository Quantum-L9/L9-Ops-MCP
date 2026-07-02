# --- L9_META ---
# l9_schema: 1
# artifact_type: documentation
# tags: ['docs', 'architecture', 'context-engineering', 'implementation-plan']
# retrieval: on_demand
# status: active
# --- /L9_META ---

# L9 Precision Context Injection: P1-P8 Implementation Plan

**Objective:** Transition the L9 Kernel system from "good context injection" (monolithic file loads) to "precision context injection" (progressive, tier-based disclosure). This plan details the exact implementation steps for the 8 priority improvements identified in `L9KernelsasContextEngineering.md`.

## Executive Summary

Currently, L9 kernels inject their entire YAML/Markdown body into the context window upon activation. This consumes budget upfront with governance metadata and universal rules that aren't needed for execution.

By implementing a **3-Tier Progressive Disclosure Architecture**, we will reduce context bloat, improve the `moderouter`'s accuracy, and enable skills to be consumed externally via standard `SKILL.md` wrappers.

---

## The 3-Tier Disclosure Architecture

All kernels will be restructured into three explicit load tiers:

1. **Tier 1 (Activation Header):** Loaded by `moderouter` at activation check. Contains `kernel_id`, `ring`, `overload_weight`, and a dispatch-optimized `description`. (~150 tokens)
2. **Tier 2 (Task Body):** Loaded after task is confirmed relevant. Contains `behavior`, `session_hooks`, and `init`. (~300-800 tokens)
3. **Tier 3 (Governance Metadata):** Loaded only during audit or governance passes. Contains `compatibility`, `routing_hints`, and `convergence_footer`.

---

## P1: Dispatch-Optimized Tier 1 Descriptions

**Current State:** Kernel `description` fields explain implementation history (e.g., "Closes GAP-08...").
**Target State:** `description` fields act as routing tokens answering What, When, and Signal vocabulary.

**Implementation Steps:**
1. Update `docs/kernels/R5/context_budget_kernel.v1.yaml`:
   - Move current `meta_context.description` to a new `meta_context.changelog` field.
   - Write a new `description` at the root level using the Trigger Triad (Capability, Trigger Conditions, User Vocabulary).
2. Repeat for all R5 kernels (`memory_admission`, `model_governance`, `preferences`, `trust_ladder`).
3. Update R0 `soul_kernel.v1.yaml` with a clear identity-lock description.
4. **Validation:** Run `make validate-wiring` to ensure schema compliance.

## P2: Defer Governance Metadata to Tier 3

**Current State:** `convergence_footer` and `compatibility` blocks load into active context.
**Target State:** Move these to a distinct `tier3_load` block.

**Implementation Steps:**
1. In all kernel YAMLs, create a new root key: `tier3_governance`.
2. Move `convergence_footer`, `compatibility`, and `routing_hints` into this block.
3. Update the `moderouter` logic (in `src/l9_ops_mcp/transport.py` or the agent system reading these files) to only parse root and `tier2_body` during standard execution, explicitly ignoring `tier3_governance` unless `audit_mode=True`.

## P3: Universal Hard Bans Deduplication

**Current State:** Universal rules are repeated inside individual kernel `hard_bans` or `behavior` blocks.
**Target State:** A single `docs/universal_hardbans.md` loaded once at R0.

**Implementation Steps:**
1. We already have `docs/universal_hardbans.md` created.
2. Audit all R5 kernels and `l9_coding_kernel.v1.md` / `l9_build_kernel.v1.md`.
3. Remove any ban that duplicates the 8 rules in `universal_hardbans.md` (e.g., "MUST NOT execute god-mode tool calls").
4. Add a pointer in each kernel: `universal_bans: "See docs/universal_hardbans.md"`.

## P4: SKILL.md Wrappers for High-Use Kernels

**Current State:** Kernels are only consumable natively by the L9 router.
**Target State:** High-use kernels have `SKILL.md` wrappers for external consumption.

**Implementation Steps:**
1. Create `skills/kernels/context-budget-guard/SKILL.md`.
2. Create `skills/kernels/sandbox-isolation/SKILL.md`.
3. Create `skills/kernels/agent-observability/SKILL.md`.
4. Ensure the `SKILL.md` maps the YAML `description` to its own description, and points to the YAML as its `kernel-source`.
5. Add these new skills to `skills/INDEX.yaml`.

## P5: Restructure Monolithic Pipeline Playbook

**Current State:** `playbooks/microservice-build/source/L9-Microservice-Build-Pipeline.md` is 1,426 lines.
**Target State:** The playbook acts as an orchestration manifest, loading steps on-demand.

**Implementation Steps:**
1. We already have the structure started in `playbooks/microservice-build/PLAYBOOK.md` and `steps/`.
2. Extract the remaining content from `L9-Microservice-Build-Pipeline.md` into individual step files (`step-02-contracts.md`, `step-03-implementation.md`, etc.).
3. Extract data types into `playbooks/microservice-build/data-types/`.
4. Archive the monolithic `source/L9-Microservice-Build-Pipeline.md` to prevent accidental full-load.

## P6: Expand Relevance Keywords

**Current State:** `relevance_keys` or `tags` are short technical labels.
**Target State:** Arrays include natural language user phrasing.

**Implementation Steps:**
1. Edit `docs/kernels/R5/context_budget_kernel.v1.yaml`: add `"losing context", "too long", "summarize earlier work"`.
2. Edit `docs/kernels/R5/trust_ladder_kernel.v1.yaml`: add `"permissions", "am I allowed to", "authorization", "access denied"`.
3. Edit `docs/kernels/R5/memory_admission_kernel.v1.yaml`: add `"remember this", "save for later", "store fact"`.

## P7: Add Eval Status and Last Tested Fields

**Current State:** Missing operational metadata in YAML kernels.
**Target State:** All kernels declare their testing reality.

**Implementation Steps:**
1. Add `last_tested: "YYYY-MM-DD"` and `eval_status: "untested" | "passing" | "failing"` to the `meta_context` block of all R0 and R5 kernels.
2. Update the `kernel.canonical.schema.json` to require these fields.

## P8: Enforce `tier2_load: onTaskConfirm` in Router

**Current State:** `moderouter` injects the whole file upon Tier 1 match.
**Target State:** `moderouter` separates evaluation from injection.

**Implementation Steps:**
1. Modify the MCP Context Broker's retrieval logic (`src/l9_ops_mcp/transport.py` or equivalent).
2. When building a TransportPacket, if a kernel is requested, read the file and assemble the `payload` using ONLY the Tier 1 and Tier 2 sections.
3. Explicitly strip the `tier3_governance` section before emitting the TransportPacket to the downstream consumer.

---

## Execution Sequence

To implement this without breaking the `l9-ops-mcp` package:
1. Update `kernel.canonical.schema.json` to support the new tier structure.
2. Run a script to migrate the 6 YAML kernels to the new structure (P1, P2, P6, P7).
3. Manually strip duplicate bans (P3).
4. Generate the `SKILL.md` wrappers (P4).
5. Split the remaining monolithic playbook (P5).
6. Update the Python MCP transport layer to enforce the tiers (P8).
7. Run `make ci` to validate all wiring and schemas.

**Context Window Usage: [14%]**
