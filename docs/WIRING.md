---
l9_schema: 1
artifact_type: documentation
tags: ['docs', 'wiring', 'ci-proof']
retrieval: on_demand
status: active
---
# L9-Ops-MCP Structural Wiring

## Authority and scope

This consolidated repository does **not** have an authoritative root `MANIFEST.json`. `config/MANIFEST.json` describes an older upstream pack with a `files` map; it is provenance, not the typed registry/dependency schema expected by the legacy tooling. Neither validator falls back to that pack or succeeds after checking zero artifacts.

`scripts/repo_structure.py` provides a read-only inventory shared by wiring and impact analysis. Canonical kernel identity, parsing, and SHA-256 verification come from the existing `l9_ops_mcp.kernel_registry.KernelRegistry`, using `AGENT_RETRIEVAL_INDEX.yaml` and `schemas/kernel.canonical.schema.json`. The validator requires a nonempty canonical registry, checks index paths and containment, compares the canonical kernel tree against registered paths, and verifies canonical kernels are linked by `AGENTS.md`.

Skills, playbooks, and prompts are discovered from their actual entrypoint files. Scoped directory IDs distinguish repeated skill names: for example, `harness/optimize-kernel` and `meta/optimize-kernel`. Dependency aliases resolve only when unique. Declared dependency lists and playbook step/handoff file references must resolve; a bare mention of a kernel in prose is not a dependency declaration. Missing hard dependencies are failures, not inferred empty lists.

## Proof surfaces

| Surface | Structural proof |
|---|---|
| `AGENTS.md` | Local links resolve to real files within the repository; absolute paths, encoded escapes, and escaping symlinks fail. |
| Canonical kernel registry/index | Nonempty discovery, unique IDs, real indexed files, canonical tree/index parity, verified kernel digests. |
| Artifact declarations | Typed dependency lists, known/unique targets, declared step files, playbook handoff/step path references, and `ARTIFACT_MANIFEST.yaml` artifact paths. |
| Make commands | Parent-owned `validate_helpers.read_makefile_tree` expands literal contained includes such as `Repo.mk` without executing Make recipes. Referenced scripts exist. |
| GitHub Actions | Both `.yaml` and `.yml` workflow jobs/steps are checked; literal repository script invocations and local actions resolve. |
| Python syntax | Repository Python source files under `scripts`, `src`, and `tests` parse with `ast`. |
| Advertised commands | Existing `validate_command_parity.py` checks README/AGENTS/workflow Make commands against the included Make target tree. |
| Console scripts | Existing `validate_pyproject_entrypoints.py` imports the `pyproject.toml` entrypoints and requires callables, using the current Python environment. |

An absent optional upstream workflow script whose invocation is protected by a same-path literal `if [ -f path ]; then` or executable check is `NOT_APPLICABLE_WITH_REASON`. An unguarded invocation is a failure. This optional-script handling does not bypass repository authority: the wiring/impact CLIs always load the current structural inventory and fail on malformed or empty authority.

## Commands

Run these with the repository's declared dependencies installed:

```sh
python3 scripts/validate_wiring.py --all
python3 scripts/validate_wiring.py --id l9_build_kernel.v1
python3 scripts/validate_wiring.py --type skill
python3 scripts/impact_analysis.py --all
python3 scripts/impact_analysis.py --kernel-id trust_ladder_kernel.v1
python3 scripts/impact_analysis.py --changed docs/kernels/R5/trust_ladder_kernel.v1.yaml
```

`--root /absolute/repository/path` is supported for explicit checkout selection and outside-working-directory execution. The default root is determined from the script location, not the caller's working directory. `--id`, `--type`, and `--all` remain accepted by the wiring CLI; selections affect reporting, never suppress broken global authority. Impact also accepts `--id` as an alias for `--kernel-id`, and `--json` for machine-readable output. Changed-file resolution matches the exact contained registry path, never a basename or suffix.

A real legacy root manifest with `kernels.registry` and other typed artifact registries remains supported. Each entry requires an ID and a real `file` path; legacy `dependencyGraph.skillsRequiringKernels` and `playbookKernelRequirements` are validated. An explicit contained `--manifest` path can select such a pack. Unknown schemas, malformed sections, missing files, invalid dependency sources/targets, or an empty kernel registry fail closed.

## Impact meaning

Impact analysis traverses only actual declared dependency edges, including kernel-to-kernel requirements and declared skill/playbook requirements. It reports direct and transitive dependents. Invalid structural declarations prevent an impact result instead of producing misleading zero-impact success. With no declared dependents, risk is `UNKNOWN`, not an assertion that changing a kernel is safe. Runtime consumers, prose references, undeclared integrations, and eval outcomes remain outside this bounded graph.

## Current readiness limitations

The historical claim that all artifacts were fully wired is not evidence for this consolidated checkout. At baseline `fecdd927`, the canonical registry contains eight kernels; the actual entrypoint inventory contains 32 artifacts. The structural checker exposes remaining active gaps and historical limitations rather than repairing content by fabrication:

- `model_governance_kernel.v1` requires `developer_core_kernel.v1`, which is not in canonical kernel authority.
- With explicit user approval, `playbooks/microservice-build/PLAYBOOK.md` is now `status: superseded` and points to the existing `../new-constellation-node/PLAYBOOK.md`. AGENTS marks the existing replacement primary/active and the old guide historical/non-executable. All original historical requirements and body text remain preserved. Five noncanonical kernel requirements and three unavailable declared step files are reported as `UNKNOWN` historical readiness, not runtime pass or implemented steps. The 17-step design is not implemented or certified complete; the replacement is not asserted to implement every proposed historical capability.
- The runtime registry records `preferences_kernel.v1` and `soul_kernel.v1` as schema-invalid. Wiring reports that fact as `UNKNOWN` for content applicability; it does not change the registry's fail-closed resolver behavior or pretend that a structural pass validates those kernels.

Supersession is a typed, fail-closed playbook contract, not a boolean ignore flag. `status: superseded` requires an explicit `superseded_by` path relative to the declaring playbook. The replacement must be real, contained, distinct, the same artifact kind, registered, AGENTS-linked, and non-superseded/executable. Supersession chains/cycles, escaping paths, missing targets, invalid replacement dependencies, and missing replacement step files fail. All active replacement declarations are checked by the normal gate. Original unavailable declarations remain visible in historical diagnostics and cannot be mistaken for runtime dependencies. No other artifact is automatically archived or exempted by this authorization.

Structural wiring is **not** content evaluation. It does not require fabricated eval fixtures, add missing convergence dates, rewrite kernel doctrine, fill placeholders, run promptfoo, or assert authored completeness. Content/runtime readiness and environment-dependent entrypoint imports need their own evidence. See [CI Proof Contract](CI_PROOF_CONTRACT.md) and [Regression Guard](../REGRESSION_GUARD.md).
