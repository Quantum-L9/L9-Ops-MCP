---
id: "L9-Ops-MCP.context.docs_repo_identity__md"
title: "REPO IDENTITY"
artifact_type: "context"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "docs/REPO_IDENTITY.md"
content_hash: "08001922d4cded5ff1e56018e549b5a39b0a96c8c01edb5db43be4df895367d9"
token_cost_estimate: 169
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "domain_agent"
description: "Unknown"
activation_signals: ["agent"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
---
# Repo Identity

L9-Ops-MCP is the Quantum-L9 MCP context control plane.

It bridges artifact metadata into Graphiti and serves bounded context slices to agents over MCP. It is not the durable memory module. Graphiti remains the backing graph and memory substrate.

## First-Class Boundary

```text
metadata injection + graph bridge + MCP context serving = this repo
durable graph memory + temporal fact storage = Graphiti / Neo4j
agent reasoning + task execution = consuming agents
```

## Architectural Rule

All agent-facing graph access must go through MCP tools or validated context-slice contracts. Direct raw graph access is not a supported path for ordinary agents.
