# --- L9_META ---
# l9_schema: 1
# component: conftest
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

"""L11 Test Fixtures.

DORA:
    component_id: test-l11-conftest
    tier: 2
    lifecycle: production
    owner: platform-engineering
"""
from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def sample_config() -> dict[str, Any]:
    """Minimal L11 pipeline config for unit tests."""
    return {
        "detection": {
            "deterministic_layer": {
                "required": True,
                "blocks_merge": True,
                "engines": [
                    {"name": "ruff", "enabled": True},
                    {"name": "mypy", "enabled": True},
                    {"name": "bandit", "enabled": True},
                    {"name": "semgrep", "enabled": True, "rules_dir": ".semgrep/l9-rules.yaml"},
                    {"name": "adr_compliance", "enabled": True},
                    {"name": "complexity_threshold", "enabled": True, "max_cyclomatic": 15},
                ],
                "l9_ci_scripts": {
                    "enabled": False,
                    "scripts": [],
                },
                "test_suite": {
                    "enabled": False,
                    "args": ["tests/", "--tb=short", "-q", "-x"],
                    "ignore": [],
                    "coverage": {"min_percent": 80.0},
                },
            },
        },
        "state_management": {
            "debt_graph": {
                "backend": "json",
                "uri_env": "NEO4J_URI",
                "user_env": "NEO4J_USER",
                "password_env": "NEO4J_PASSWORD",
            },
            "json_fallback": {
                "enabled": True,
                "path": "",  # Set per-test via tmp_path
            },
        },
        "risk_model": {
            "weights": {
                "severity": {"P0": 100, "P1": 80, "P2": 50, "P3": 20},
                "blast_radius": {
                    "core_kernel": 100,
                    "api_layer": 80,
                    "agent_logic": 60,
                    "worker": 50,
                    "utility": 40,
                },
                "service_criticality": {
                    "tier1_production": 100,
                    "tier2_staging": 60,
                    "tier3_dev": 20,
                },
            },
            "thresholds": {"block_pr": 85, "create_issue": 65, "backlog": 40},
            "aging_policy": {
                "p3_to_p2_days": 60,
                "p2_to_p1_days": 30,
                "p1_to_p0_days": 60,
            },
        },
        "execution": {
            "triggers": {
                "pr": {
                    "incremental": True,
                    "deterministic_only": True,
                    "ai_enrichment_async": False,
                },
                "schedule": {
                    "nightly_full_scan": True,
                    "ai_enrichment": False,
                },
            },
        },
        "remediation": {
            "auto_fix": {
                "enabled": False,
                "supported_categories": ["linting_errors", "import_sorting"],
                "safety": {
                    "require_passing_tests": True,
                    "shadow_diff_validation": True,
                    "rollback_on_failure": True,
                    "require_approval": True,
                },
            },
        },
    }


@pytest.fixture
def sample_finding() -> dict[str, Any]:
    """Sample finding for risk scoring tests."""
    return {
        "tool": "ruff",
        "rule": "E501",
        "message": "Line too long (120 > 88 characters)",
        "file": "core/kernel/engine.py",
        "line": 42,
        "severity": "P2",
        "ai_enrichment": {},
    }


@pytest.fixture
def sample_findings() -> list[dict[str, Any]]:
    """Batch of findings for graph/orchestrator tests."""
    return [
        {
            "tool": "bandit",
            "rule": "B101",
            "message": "Use of assert detected",
            "file": "core/kernel/engine.py",
            "line": 10,
            "severity": "P1",
        },
        {
            "tool": "ruff",
            "rule": "E501",
            "message": "Line too long",
            "file": "api/routes.py",
            "line": 55,
            "severity": "P2",
        },
        {
            "tool": "adr_checker",
            "rule": "ADR-0019",
            "message": "stdlib logging in agents/planner.py",
            "file": "agents/planner.py",
            "line": 3,
            "severity": "P0",
        },
    ]
