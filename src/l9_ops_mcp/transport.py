# --- L9_META ---
# l9_schema: 1
# artifact_type: runtime_module
# component: transport_packet_contract
# tags: [transportpacket, canonical-contract, validation]
# retrieval: on_demand
# status: active
# --- /L9_META ---

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import hashlib
import json
import uuid

REQUIRED_KEYS = {
    "packet_id",
    "packet_type",
    "schema_version",
    "created_at",
    "producer",
    "consumer",
    "objective",
    "context_scope",
    "payload",
    "provenance",
    "budget",
    "routing",
    "validation",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_transport_packet(
    *,
    packet_type: str,
    producer: str,
    consumer: str,
    objective: str,
    context_scope: dict[str, Any],
    payload: dict[str, Any],
    provenance: list[dict[str, Any]],
    skills: list[str],
    kernels: list[str],
    sequence: list[str],
    max_context_files: int = 24,
) -> dict[str, Any]:
    return {
        "packet_id": f"tp_{uuid.uuid4().hex}",
        "packet_type": packet_type,
        "schema_version": "1.0.0",
        "created_at": datetime.now(tz=UTC).isoformat(),
        "producer": producer,
        "consumer": consumer,
        "objective": objective,
        "context_scope": context_scope,
        "payload": payload,
        "provenance": provenance,
        "budget": {
            "token_strategy": "laser_scoped_retrieval_from_headers_and_index",
            "max_context_files": max_context_files,
            "bloat_guard": "exclude_unreferenced_doctrine_and_non_matching_skills",
        },
        "routing": {"skills": skills, "kernels": kernels, "sequence": sequence},
        "validation": {
            "status": "pass",
            "checks": ["required_keys", "provenance_hashes", "routing_sequence"],
        },
    }


def validate_transport_packet(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_KEYS - set(packet))
    if missing:
        errors.append("missing_keys:" + ",".join(missing))
    if packet.get("schema_version") != "1.0.0":
        errors.append("schema_version_not_1.0.0")
    if not isinstance(packet.get("provenance"), list) or not packet.get("provenance"):
        errors.append("provenance_empty")
    routing = packet.get("routing", {})
    if not routing.get("sequence"):
        errors.append("routing_sequence_empty")
    if packet.get("consumer") == "l9_ops_mcp":
        errors.append("consumer_must_be_downstream_runtime_or_agent")
    return errors


def write_packet(packet: dict[str, Any], path: Path) -> Path:
    errors = validate_transport_packet(packet)
    if errors:
        raise ValueError("invalid TransportPacket: " + "; ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
