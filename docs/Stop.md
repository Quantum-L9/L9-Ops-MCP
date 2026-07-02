---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# L9 Stop Hook
## Source: danielmiessler/Personal_AI_Infrastructure#HookSystem.md (Stop event type)

Fires when a playbook execution attempts to terminate.
Acts as the final quality gate — can BLOCK premature exit.

## Gates
1. **All required steps completed?** Check `completed_steps` vs `required_steps` in spec.
   → If incomplete without a valid exit condition: BLOCK with `l9.stop.incomplete_execution`

2. **All required outputs populated?** Validate `$.outputs` against spec output schema.
   → If missing required fields: BLOCK with `l9.stop.missing_outputs`

3. **Audit chain intact?** Verify hash chain for this run's audit records.
   → If chain broken: BLOCK with `l9.stop.audit_chain_broken`

4. **Open compensation actions?** Are any pending saga compensations unresolved?
   → If YES and run_status != `compensated`: BLOCK

5. **ALLOW STOP**: Write final run record to audit log. Update kernel continuity memory.
