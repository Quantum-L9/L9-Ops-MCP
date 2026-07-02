---
l9_schema: 1
artifact_type: contract
component: transport_packet
tags: [transport, packet, canonical-contract]
status: active
---
# TransportPacket Contract

TransportPacket is the canonical inter-component contract for PR review, context routing, skill/kernel selection, and remediation output handoff. PacketEnvelope is deprecated and must not be used for active runtime exchange.

Schema: `schemas/transport-packet.schema.json`

Required flow:

1. PR review request enters the packet builder.
2. Builder emits a scoped `TransportPacket`.
3. Router selects exact skills, kernels, playbooks, and source files from retrieval metadata.
5. Validator checks packet shape, provenance, routing sequence, and context budget.
