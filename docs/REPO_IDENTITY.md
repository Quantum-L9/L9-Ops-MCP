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
