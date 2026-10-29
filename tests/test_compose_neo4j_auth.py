"""F-085 (WU-43 compose part): the Neo4j container's password comes from
L9_NEO4J_PASS, the variable install.sh, preflight.sh and the MCP config
writers already use, instead of a hard-coded literal that ignores it."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.neo4j.yml"


def _neo4j_auth() -> str:
    doc = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    return str(doc["services"]["neo4j"]["environment"]["NEO4J_AUTH"])


def test_neo4j_auth_reads_l9_neo4j_pass() -> None:
    assert _neo4j_auth() == "neo4j/${L9_NEO4J_PASS:-l9_local_dev_pw}"


def test_compose_default_matches_env_example() -> None:
    match = re.fullmatch(r"neo4j/\$\{L9_NEO4J_PASS:-(?P<default>[^}]*)\}", _neo4j_auth())
    assert match is not None
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert f"L9_NEO4J_PASS={match['default']}" in example.splitlines()
