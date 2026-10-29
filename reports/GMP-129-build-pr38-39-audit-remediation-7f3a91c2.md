# GMP-129

**Task:** Build pr38_39_audit_remediation_7f3a91c2.plan.md (PR #39 branch: T6-T8)
**Tier:** RUNTIME

## TODOs

- T6: src/l9_ops_mcp/server.py REPLACE Commit T1-T5 on agent/claude/remed-integration (one scoped commit per finding), run make ci there, then merge that branch into agent/claude/remed-obs-followup with a merge commit (no rebase) in the #39 worktree and re-run make ci.
- T6.2: src/l9_ops_mcp/memory_ops.py REPLACE Commit T1-T5 on agent/claude/remed-integration (one scoped commit per finding), run make ci there, then merge that branch into agent/claude/remed-obs-followup with a merge commit (no rebase) in the #39 worktree and re-run make ci.
- T6.3: src/l9_ops_mcp/trust_ladder.py REPLACE Commit T1-T5 on agent/claude/remed-integration (one scoped commit per finding), run make ci there, then merge that branch into agent/claude/remed-obs-followup with a merge commit (no rebase) in the #39 worktree and re-run make ci.
- T7: scripts/l11/deterministic_engine.py REPLACE F-pr38-14: in scripts/l11/deterministic_engine.py run _unimplemented_check_errors() before the empty-file-list early return so an enabled-but-unimplemented check fails scan([]); add an empty-list case to TestUnimplementedChecksFailClosed.
- T7.2: scripts/test_deterministic_engine.py REPLACE F-pr38-14: in scripts/l11/deterministic_engine.py run _unimplemented_check_errors() before the empty-file-list early return so an enabled-but-unimplemented check fails scan([]); add an empty-list case to TestUnimplementedChecksFailClosed.
- T8: tests/test_ci_workflow_paths_filter.py REPLACE F-pr38-15: tests/test_ci_workflow_paths_filter.py derives protected patterns exactly as the gate does (subsystem protected_paths via the gate's accessor) and adds a subsystem fixture case.
