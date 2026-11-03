# >>> l9:meta >>>
# id: L9-Ops-MCP.source.src_l9_ops_mcp_models__py
# title: models
# artifact_type: source
# mcp_primitive: resource
# callable: false
# retrievable: true
# injectable: true
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: src/l9_ops_mcp/models.py
# content_hash: 115657dde09debc2cdeb08ba9b2863128f1ad63be5f53fd71f234ec84ef4931f
# token_cost_estimate: 360
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
"""Pydantic models — RuntimePayload, ContextSlice, MemoryCandidate."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

TrustLevel = Literal["L0", "L1", "L2", "L3", "L4", "L5"]


class ContextFact(BaseModel):
    uuid: str = ""
    fact: str
    valid_at: datetime | None = None
    invalid_at: datetime | None = None
    group_id: str = ""
    score: float = 0.0
    token_estimate: int = 0


class ContextSlice(BaseModel):
    tier1_load_bearing: list[ContextFact] = Field(default_factory=list)
    tier2_examples: list[ContextFact] = Field(default_factory=list)
    tier3_stakes: list[ContextFact] = Field(default_factory=list)
    token_count: int = 0


class RuntimePayload(BaseModel):
    agent_id: str
    profile_id: str = "igor-beylin"
    substrate: str = "cursor"
    trust_level: TrustLevel
    allowed_scopes: list[str]
    context_slice: ContextSlice
    budget_remaining_tokens: int
    readonly: Literal[True] = True  # handoff_packets_are_views invariant


class MemoryCandidate(BaseModel):
    body: str
    source_agent_id: str
    session_id: str
    origin_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    group_ids: list[str] = Field(default_factory=list)
    semantic_score: float = 0.0
    trust_level: TrustLevel = "L2"
    metadata: dict[str, Any] = Field(default_factory=dict)
