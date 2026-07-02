---
title: "cursor-memory-kernel — Cursor Agent Memory Protocol Skill"
purpose: "Full memory lifecycle management for Cursor AI agent sessions: injection, retrieval, write, dedupe, session lifecycle, degraded-mode fallback."
summary: "5-layer context injection hierarchy, 12 CLI commands, 6 lifecycle hooks, packet taxonomy with TTLs, decision logic gates, anti-patterns, and degraded-mode behavior when MCP is unavailable."
version: "2.0.0"
source_files: ["IgorOS/cursor_memory_kernel.yaml"]
created: "2026-06-18"
owner: "Igor Beylin"
tags: ["memory", "cursor", "MCP", "context-injection", "session-lifecycle", "graphiti", "R1"]
domain: "global"
type: "skill"
ring: "R1"
production_ready: true
retrieval_keys: ["memory", "cursor memory", "context injection", "session start", "MCP", "graphiti", "memory protocol"]
trigger_description: "Load at: session start, task context change, error encounter, user correction, session end."
---

# cursor-memory-kernel

## Trigger
Invoke at: session start, task context change, error encounter, user correction, session end.

## Injection Layers (Priority Order)

| Layer | Description | Priority | Max | Kinds | Refresh |
|---|---|---|---|---|---|
| L1 | Igor coding style, patterns, explicit preferences | highest | 5 | preference | session_start |
| L2 | Past mistakes and corrections | high | 5 | lesson | session_start |
| L3 | Current task domain context | medium | 5 | insight, note, context | task_change |
| L4 | Recent session activity and continuity | medium | 3 | any | continuous |
| L5 | Anti-patterns to avoid for current task | high | 3 | error, lesson | task_change |

## Packet Taxonomy

| Kind | TTL | Examples |
|---|---|---|
| preference | permanent | Igor prefers surgical edits over full rewrites |
| lesson | permanent | GlobalCommands is in Dropbox NOT Library |
| error | 30d | ConnectionRefused 5432 check postgres container |
| insight | permanent | Factory pattern accepted in L9 for configured instances |
| note | 30d | Working on memory kernel refactor |
| context | permanent | SESSION 2026-01-25 15 packets key work on memory |

## CLI Commands
All: python3 agents/cursor/cursormemoryclient.py COMMAND

| Command | When |
|---|---|
| health | Session start — always first |
| inject TASK | New task or need full context |
| search QUERY | Need specific memory |
| write CONTENT --kind KIND | New lesson or preference to persist |
| warn TASK | Before risky or familiar task |
| fix-error ERROR | On error encounter |
| dedupe-check CONTENT | Before any write |
| session-close | Session end |
| session-resume --task TASK | Session start when resuming |
| temporal QUERY --since WINDOW | Time-scoped query |

## Decision Logic

```
before_code_generation:
  - search_similar_past_work
  - check_anti_patterns
  - load_preferences

before_file_modification:
  - check_protected_file_warnings
  - load_file_specific_lessons

before_destructive_operation:
  - search_past_failures
  - load_rollback_patterns
  - require_explicit_approval

on_user_correction:
  - extract_lesson_or_preference
  - dedupe_check
  - write_to_memory
  - acknowledge
```

## Lifecycle Hooks

```
session_start:    health_check, inject_preferences, inject_lessons, resume_session_context
task_change:      inject_domain_context, warn_for_task, load_task_patterns
error_detected:   search_similar_errors, load_known_fixes, suggest_remediation
user_corrects:    extract_lesson, dedupe_check, write_to_memory, acknowledge_learning
session_end:      summarize_session, create_embedding_anchor, save_context, update_workflow_state
```

## Anti-Patterns

| Anti-Pattern | Prevention |
|---|---|
| memory_without_health_check | Always run health at session start |
| duplicate_writes | Always dedupe-check before write |
| forgotten_context | Inject at session start AND task change |
| silent_learning | Always write lesson or preference on user correction |
| stale_session_context | session-close at end, session-resume at start |
| over_reliance_on_memory | Current user input always takes precedence |

## Degraded Mode (MCP unavailable)
Use file-based context only via workflow_state.md. Skip memory writes. Notify user.

## Troubleshooting

| Code | Cause | Fix |
|---|---|---|
| 1010 | Cloudflare blocking | Use direct IP 46.62.243.82 |
| governance_context_required | REST endpoint | Use mcp_call endpoint |
| invalid_api_key | Missing auth | Set MCP_API_KEY_C env var |
