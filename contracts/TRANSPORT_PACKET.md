---
l9_schema: 1
artifact_type: "contract"
component: "transport_packet"
tags: ["transport", "packet", "canonical-contract"]
status: "active"
id: "L9-Ops-MCP.context.contracts_transport_packet__md"
title: "TRANSPORT PACKET"
mcp_primitive: "resource"
callable: true
retrievable: true
injectable: true
namespace: "L9-Ops-MCP"
sharing_scope: "agnostic"
source_path: "contracts/TRANSPORT_PACKET.md"
content_hash: "7bf721bbf4f9bf2f498bb8759cac0ba789b459781556a38704e4701eb5ba64fa"
token_cost_estimate: 148
authority: "Quantum-L9"
created_or_detected_at: "Unknown"
family: "auditor"
description: "Unknown"
activation_signals: ["review", "kernel", "contract"]
input_contract: "Unknown"
output_contract: "Unknown"
validation_gates: "Unknown"
stop_conditions: "Unknown"
---
# TransportPacket Contract

TransportPacket is the canonical inter-component contract for PR review, context routing, skill/kernel selection, and remediation output handoff. PacketEnvelope is deprecated and must not be used for active runtime exchange.

Schema: `schemas/transport-packet.schema.json`

Required flow:

1. PR review request enters the packet builder.
2. Builder emits a scoped `TransportPacket`.
3. Router selects exact skills, kernels, playbooks, and source files from retrieval metadata.
5. Validator checks packet shape, provenance, routing sequence, and context budget.
