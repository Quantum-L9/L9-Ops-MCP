# --- L9_META ---
# l9_schema: 1
# component: loader
# artifact_type: runtime
# tags: [l9-action-governor, runtime]
# retrieval: on_demand
# status: active
# --- /L9_META ---

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel

from .models import (
    ConvergencePlan,
    GovernanceGraphIR,
    GovernanceScores,
    RuntimeFindings,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def load_model(model: type[ModelT], path: Path) -> ModelT:
    if path.suffix.lower() == ".json":
        data = read_json(path)
    else:
        data = read_yaml(path)
    return model.model_validate(data)


def load_run(
    run_dir: Path,
) -> tuple[GovernanceGraphIR, GovernanceScores, ConvergencePlan, RuntimeFindings]:
    graph = load_model(GovernanceGraphIR, run_dir / "governance_graph_ir.json")
    scores = load_model(GovernanceScores, run_dir / "governance_scores.yaml")
    plan = load_model(ConvergencePlan, run_dir / "convergence_plan.yaml")
    findings_path = run_dir / "runtime_findings.yaml"
    findings = (
        RuntimeFindings()
        if not findings_path.exists()
        else load_model(RuntimeFindings, findings_path)
    )
    return graph, scores, plan, findings
