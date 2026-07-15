# --- L9_META ---
# l9_schema: 1
# component: planner
# artifact_type: runtime
# tags: [l9-action-governor, runtime]
# retrieval: on_demand
# status: active
# --- /L9_META ---

from __future__ import annotations

import re
from collections import defaultdict

from .models import (
    ActionGovernorResult,
    ComponentScore,
    ConvergenceAction,
    ConvergencePlan,
    DecisionClass,
    DecisionPacket,
    GovernanceGraphIR,
    GovernanceScores,
    GraphNode,
    RenamePlanItem,
    ReorgPlanItem,
    RuntimeFinding,
    RuntimeFindings,
)
from .scorer import priority_score

DEFAULT_TARGETS: dict[str, str] = {
    "kernel": "/l9_system/00_governance_spine",
    "intake": "/l9_system/01_intake",
    "inventory": "/l9_system/02_inventory_node",
    "topology": "/l9_system/03_topology_reconstruction",
    "governance": "/l9_system/04_governance_evaluation",
    "convergence": "/l9_system/05_convergence_planning",
    "action_governor": "/l9_system/06_action_governor",
    "remediation": "/l9_system/07_remediation_engine",
    "runtime": "/l9_system/08_runtime_enforcement",
    "report": "/l9_system/09_reports",
    "archive": "/l9_system/90_archive",
    "experiment": "/l9_system/99_experiments",
}


class ActionGovernor:
    def decide(
        self,
        graph: GovernanceGraphIR,
        scores: GovernanceScores,
        plan: ConvergencePlan,
        findings: RuntimeFindings,
    ) -> ActionGovernorResult:
        score_by_id = {item.component_id: item for item in scores.scores}
        actions_by_id = self._group_actions(plan.actions)
        findings_by_id = self._group_findings(findings.findings)

        decisions: list[DecisionPacket] = []
        rename_items: list[RenamePlanItem] = []
        reorg_items: list[ReorgPlanItem] = []

        for node in graph.nodes:
            component_score = score_by_id.get(node.node_id, self._default_score(node.node_id))
            actions = actions_by_id.get(node.node_id, [])
            node_findings = findings_by_id.get(node.node_id, [])
            primary_action = self._primary_action(actions)
            canonical_name = self._canonical_name(node, primary_action)
            target_folder = self._target_folder(node, primary_action)
            decision_class = self._decision_class(component_score, primary_action, node_findings)
            blockers = primary_action.blockers if primary_action else []
            priority = primary_action.priority if primary_action else "medium"
            score_value = priority_score(component_score, node_findings, priority, len(blockers))
            evidence = self._evidence(node, primary_action, node_findings)
            reason = self._reason(node, decision_class, component_score, node_findings, blockers)
            next_action = self._next_action(decision_class, canonical_name, target_folder, blockers)

            decisions.append(
                DecisionPacket(
                    decision_id=f"decision_{node.node_id}",
                    rank=0,
                    component_id=node.node_id,
                    component_name=node.name,
                    canonical_name=canonical_name,
                    decision_class=decision_class,
                    priority_score=score_value,
                    confidence=self._confidence(component_score, actions, node_findings),
                    reason=reason,
                    next_action=next_action,
                    evidence=evidence,
                    dependencies=node.dependencies,
                    risks=self._risks(component_score, node_findings, blockers),
                    target_folder=target_folder,
                    approval_required=True,
                )
            )

            if canonical_name != node.name:
                rename_items.append(
                    RenamePlanItem(
                        component_id=node.node_id,
                        current_name=node.name,
                        canonical_name=canonical_name,
                        reason="Canonical name describes durable function instead of pack history or temporary phase naming.",
                    )
                )

            if target_folder != (node.proposed_path or node.current_path):
                reorg_items.append(
                    ReorgPlanItem(
                        component_id=node.node_id,
                        current_path=node.current_path,
                        target_folder=target_folder,
                        reason="Target folder follows L9 authority placement and build sequence.",
                    )
                )

        if not decisions:
            decisions.append(self._empty_input_escalation())

        ranked = sorted(decisions, key=lambda item: item.priority_score, reverse=True)
        for index, decision in enumerate(ranked, start=1):
            decision.rank = index

        return ActionGovernorResult(
            ranked_decisions=ranked,
            execution_queue=[
                d
                for d in ranked
                if d.decision_class
                in {DecisionClass.build_now, DecisionClass.build_next, DecisionClass.build_later}
            ],
            remediation_queue=[
                d
                for d in ranked
                if d.decision_class
                in {DecisionClass.remediate_now, DecisionClass.rename, DecisionClass.reorganize}
            ],
            escalation_queue=[
                d
                for d in ranked
                if d.decision_class in {DecisionClass.escalate, DecisionClass.delete}
            ],
            rename_plan=rename_items,
            reorg_plan=reorg_items,
        )

    def _group_actions(
        self, actions: list[ConvergenceAction]
    ) -> dict[str, list[ConvergenceAction]]:
        grouped: dict[str, list[ConvergenceAction]] = defaultdict(list)
        for action in actions:
            grouped[action.component_id].append(action)
        return grouped

    def _group_findings(self, findings: list[RuntimeFinding]) -> dict[str, list[RuntimeFinding]]:
        grouped: dict[str, list[RuntimeFinding]] = defaultdict(list)
        for finding in findings:
            grouped[finding.component_id].append(finding)
        return grouped

    def _primary_action(self, actions: list[ConvergenceAction]) -> ConvergenceAction | None:
        if not actions:
            return None
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return sorted(actions, key=lambda item: order[item.priority])[0]

    def _default_score(self, component_id: str) -> ComponentScore:
        return ComponentScore(component_id=component_id)

    def _canonical_name(self, node: GraphNode, action: ConvergenceAction | None) -> str:
        if action and action.canonical_name:
            return action.canonical_name
        name = node.name.lower()
        name = re.sub(r"[^a-z0-9]+", "_", name).strip("_")
        replacements = {
            "revised_convergence_pack_v2": "l9_convergence_engine",
            "constellation_inventory_node_phase3_l9_alignment_pack_v3_1": "l9_inventory_node",
            "governanceos": "l9_governance_os",
        }
        return replacements.get(name, name if name.startswith("l9_") else f"l9_{name}")

    def _target_folder(self, node: GraphNode, action: ConvergenceAction | None) -> str:
        if action and action.target_folder:
            return action.target_folder
        text = " ".join([node.name, node.node_type, " ".join(node.capabilities)]).lower()
        for marker, folder in DEFAULT_TARGETS.items():
            if marker in text:
                return folder
        return "/l9_system/99_experiments"

    def _decision_class(
        self,
        score: ComponentScore,
        action: ConvergenceAction | None,
        findings: list[RuntimeFinding],
    ) -> DecisionClass:
        if action and action.blockers:
            return DecisionClass.escalate
        if any(f.severity == "critical" for f in findings):
            return DecisionClass.escalate
        if findings and score.governance_criticality >= 70:
            return DecisionClass.remediate_now
        if action and action.action_type in {"rename", "canonicalize_name"}:
            return DecisionClass.rename
        if action and action.action_type in {"move", "reorganize", "canonicalize_folder"}:
            return DecisionClass.reorganize
        if (
            score.strategic_value >= 75
            and score.execution_readiness >= 65
            and score.entropy_risk <= 60
        ):
            return DecisionClass.build_now
        if score.strategic_value >= 70:
            return DecisionClass.build_next
        if score.strategic_value <= 30 and score.entropy_risk >= 70:
            return DecisionClass.archive
        return DecisionClass.defer

    def _confidence(
        self,
        score: ComponentScore,
        actions: list[ConvergenceAction],
        findings: list[RuntimeFinding],
    ) -> str:
        signal_count = len(actions) + len(findings)
        if signal_count >= 2 and score.documentation_quality >= 50:
            return "high"
        if signal_count >= 1:
            return "medium"
        return "low"

    def _evidence(
        self,
        node: GraphNode,
        action: ConvergenceAction | None,
        findings: list[RuntimeFinding],
    ) -> list[str]:
        evidence = [f"node_type={node.node_type}"]
        evidence.extend(node.source_topologies)
        if action:
            evidence.extend(action.evidence)
        for finding in findings:
            evidence.extend(finding.evidence)
        return sorted(set(evidence))

    def _reason(
        self,
        node: GraphNode,
        decision_class: DecisionClass,
        score: ComponentScore,
        findings: list[RuntimeFinding],
        blockers: list[str],
    ) -> str:
        if blockers:
            return (
                f"{node.name} is blocked by {', '.join(blockers)} and requires governed escalation."
            )
        if findings:
            return f"{node.name} has runtime findings and governance criticality {score.governance_criticality}."
        if decision_class in {DecisionClass.build_now, DecisionClass.build_next}:
            return f"{node.name} has strategic value {score.strategic_value} and readiness {score.execution_readiness}."
        if decision_class == DecisionClass.archive:
            return f"{node.name} has low strategic value and high entropy risk."
        return f"{node.name} requires further evidence before irreversible action."

    def _next_action(
        self,
        decision_class: DecisionClass,
        canonical_name: str,
        target_folder: str,
        blockers: list[str],
    ) -> str:
        if blockers:
            return "Resolve blocker authority and re-run Action Governor."
        mapping = {
            DecisionClass.build_now: f"Create or harden {canonical_name} in {target_folder}.",
            DecisionClass.build_next: f"Prepare build spec for {canonical_name} after current build-now items.",
            DecisionClass.build_later: f"Keep {canonical_name} in backlog with dependency notes.",
            DecisionClass.remediate_now: f"Create remediation plan for {canonical_name} before new feature work.",
            DecisionClass.escalate: f"Escalate {canonical_name} for human approval before action.",
            DecisionClass.rename: f"Approve rename to {canonical_name}.",
            DecisionClass.reorganize: f"Approve move into {target_folder}.",
            DecisionClass.archive: f"Move {canonical_name} into archive after uniqueness check.",
            DecisionClass.delete: f"Require duplicate proof before deleting {canonical_name}.",
            DecisionClass.defer: f"Collect more evidence for {canonical_name}.",
        }
        return mapping[decision_class]

    def _risks(
        self,
        score: ComponentScore,
        findings: list[RuntimeFinding],
        blockers: list[str],
    ) -> list[str]:
        risks: list[str] = []
        if score.entropy_risk >= 70:
            risks.append("high_entropy")
        if score.drift_risk >= 70:
            risks.append("high_drift")
        if blockers:
            risks.append("blocked_by_dependencies_or_authority")
        if any(f.severity in {"critical", "high"} for f in findings):
            risks.append("runtime_risk")
        return risks

    def _empty_input_escalation(self) -> DecisionPacket:
        return DecisionPacket(
            decision_id="decision_missing_graph_nodes",
            rank=1,
            component_id="missing_graph_nodes",
            component_name="missing_graph_nodes",
            canonical_name="l9_missing_graph_nodes",
            decision_class=DecisionClass.escalate,
            priority_score=100,
            confidence="high",
            reason="No graph nodes were available for decision ranking.",
            next_action="Regenerate GovernanceGraphIR with at least one component node.",
            evidence=["empty_graph"],
            dependencies=[],
            risks=["no_decision_surface"],
            target_folder="/l9_system/04_governance_evaluation",
            approval_required=True,
        )
