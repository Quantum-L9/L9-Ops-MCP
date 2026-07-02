---
l9_schema: 1
artifact_type: documentation
tags: ['docs']
retrieval: on_demand
status: active
---
# Topology Merge Rationale

## The question

Why merge repo topology, governance topology, and runtime topology?

## Answer

Because a governor needs one surface where structure, authority, and live behavior meet.

## Three separate maps are not enough

### Repo topology

Shows what exists:

- files
- folders
- imports
- docs
- prompts
- modules
- artifact clusters

But it does not know what is allowed, risky, governed, blocked, or urgent.

### Governance topology

Shows what controls the system:

- rules
- gates
- policies
- ownership
- escalation paths
- invariants

But it does not know whether the repo is structurally coherent or full of dead artifacts.

### Runtime topology

Shows what is happening:

- failures
- traces
- incidents
- policy violations
- usage signals
- blocked executions

But it does not know whether a live failure belongs to a strategic core component or irrelevant junk.

## Unified GovernanceGraphIR

The merged graph lets the Action Governor rank action using this combined truth:

```text
artifact identity + governing authority + runtime evidence
```

That is the minimum substrate required for governed action.

## Non-goal

The merged graph does not erase source-specific evidence. Each node and edge must preserve provenance:

```yaml
source_topologies:
  - repo
  - governance
  - runtime
```

The merge is a decision substrate, not a blender.
