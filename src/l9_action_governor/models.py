# --- L9_META ---
# l9_schema: 1
# component: models
# artifact_type: runtime
# tags: [l9-action-governor, runtime]
# retrieval: on_demand
# status: active
# --- /L9_META ---

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class DecisionClass(str, Enum):
    build_now = "build_now"
    build_next = "build_next"
    build_later = "build_later"
    remediate_now = "remediate_now"
    escalate = "escalate"
    rename = "rename"
    reorganize = "reorganize"
    archive = "archive"
    delete = "delete"
    defer = "defer"


Confidence = Literal["high", "medium", "low"]


class GraphNode(BaseModel):
    node_id: str
    name: str
    node_type: str
    source_topologies: list[str] = Field(default_factory=list)
    description: str | None = None
    current_path: str | None = None
    proposed_path: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    governed_by: list[str] = Field(default_factory=list)
    runtime_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    edge_type: str
    evidence: list[str] = Field(default_factory=list)


class GovernanceGraphIR(BaseModel):
    graph_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ComponentScore(BaseModel):
    component_id: str
    structural_coherence: int = 50
    execution_readiness: int = 50
    documentation_quality: int = 50
    dependency_integrity: int = 50
    governance_criticality: int = 50
    strategic_value: int = 50
    reuse_potential: int = 50
    entropy_risk: int = 50
    drift_risk: int = 50


class GovernanceScores(BaseModel):
    scores: list[ComponentScore]


class ConvergenceAction(BaseModel):
    component_id: str
    action_type: str
    description: str
    priority: Literal["critical", "high", "medium", "low"] = "medium"
    target_folder: str | None = None
    canonical_name: str | None = None
    blockers: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class ConvergencePlan(BaseModel):
    actions: list[ConvergenceAction]


class RuntimeFinding(BaseModel):
    component_id: str
    severity: Literal["critical", "high", "medium", "low"] = "medium"
    finding_type: str
    description: str
    evidence: list[str] = Field(default_factory=list)


class RuntimeFindings(BaseModel):
    findings: list[RuntimeFinding] = Field(default_factory=list)


class DecisionPacket(BaseModel):
    decision_id: str
    rank: int
    component_id: str
    component_name: str
    canonical_name: str
    decision_class: DecisionClass
    priority_score: int
    confidence: Confidence
    reason: str
    next_action: str
    evidence: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    target_folder: str
    approval_required: bool = True


class RenamePlanItem(BaseModel):
    component_id: str
    current_name: str
    canonical_name: str
    reason: str


class ReorgPlanItem(BaseModel):
    component_id: str
    current_path: str | None
    target_folder: str
    reason: str


class ActionGovernorResult(BaseModel):
    ranked_decisions: list[DecisionPacket]
    execution_queue: list[DecisionPacket]
    remediation_queue: list[DecisionPacket]
    escalation_queue: list[DecisionPacket]
    rename_plan: list[RenamePlanItem]
    reorg_plan: list[ReorgPlanItem]
