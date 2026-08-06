# --- L9_META ---
# l9_schema: 1
# component: writer
# artifact_type: runtime
# tags: [l9-action-governor, runtime]
# retrieval: on_demand
# status: active
# --- /L9_META ---

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from .models import ActionGovernorResult
from .renderer import render_decision_report


def model_dump_yaml(obj: BaseModel | list[BaseModel]) -> str:
    if isinstance(obj, list):
        data: Any = [item.model_dump(mode="json") for item in obj]
    else:
        data = obj.model_dump(mode="json")
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def write_result(result: ActionGovernorResult, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "ranked_decisions.yaml").write_text(
        model_dump_yaml(result.ranked_decisions), encoding="utf-8"
    )
    (out_dir / "execution_queue.yaml").write_text(
        model_dump_yaml(result.execution_queue), encoding="utf-8"
    )
    (out_dir / "remediation_queue.yaml").write_text(
        model_dump_yaml(result.remediation_queue), encoding="utf-8"
    )
    (out_dir / "escalation_queue.yaml").write_text(
        model_dump_yaml(result.escalation_queue), encoding="utf-8"
    )
    (out_dir / "rename_plan.yaml").write_text(model_dump_yaml(result.rename_plan), encoding="utf-8")
    (out_dir / "reorg_plan.yaml").write_text(model_dump_yaml(result.reorg_plan), encoding="utf-8")
    (out_dir / "decision_report.md").write_text(render_decision_report(result), encoding="utf-8")
