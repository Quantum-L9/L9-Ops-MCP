# --- L9_META ---
# l9_schema: 1
# origin: l9-ops-mcp
# layer: adapter
# artifact_type: runtime_module
# component: manus_kernel_server
# tags: [manus, mcp, kernel-authority]
# owner: Quantum-L9
# retrieval: on_demand
# status: active
# --- /L9_META ---
"""Restricted Manus MCP facade for deterministic L9 kernel authority.

This process deliberately exposes only ``kernel_resolve`` from the native
L9-Ops-MCP server. It has no Graphiti, memory, secret, filesystem-write, or
network tool surface. Strict integrity checks are forced for every resolution,
so a long-lived connector cannot silently return authority after canonical
kernel bytes drift.
"""

from __future__ import annotations

import os
from typing import cast

from mcp.server.fastmcp import FastMCP

from . import server as native_server

mcp = FastMCP(
    "l9-ops-manus",
    instructions=(
        "Use this read-only MCP only to resolve deterministic canonical L9 kernel "
        "authority for a declared execution profile. It exposes no memory, Graphiti, "
        "secret, shell, deployment, repository-write, or network capabilities."
    ),
)


@mcp.tool()  # type: ignore[untyped-decorator]
async def kernel_resolve(
    profile: str,
    consumer: str,
    objective: str,
    trust_level: str,
    max_overload_weight: float,
    allow_experimental: bool = False,
) -> dict[str, object]:
    """Resolve deterministic canonical kernel authority in strict-integrity mode.

    The response is a bounded Tier-1 normative projection with provenance and a
    stable resolution digest. Errors use the native stable ``{status, code,
    message}`` envelope and never expose raw tracebacks.
    """

    os.environ["L9_KERNEL_STRICT_INTEGRITY"] = "1"
    payload = await native_server.kernel_resolve(
        profile=profile,
        consumer=consumer,
        objective=objective,
        trust_level=trust_level,
        max_overload_weight=max_overload_weight,
        allow_experimental=allow_experimental,
    )
    return cast(dict[str, object], payload)


def main() -> None:
    """Serve the restricted facade exclusively over local stdio."""

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
