# >>> l9:meta >>>
# id: L9-Ops-MCP.source.src_l9_ops_mcp_adapters_graph_sync_init__py
# title: init
# artifact_type: source
# mcp_primitive: resource
# callable: false
# retrievable: true
# injectable: true
# namespace: L9-Ops-MCP
# sharing_scope: agnostic
# source_path: src/l9_ops_mcp/adapters/graph_sync/__init__.py
# content_hash: d4689acf0fdd1834ff525936c8a5a202d0dfbc9728d8071da6afe1d98fa2a747
# token_cost_estimate: 20
# authority: Quantum-L9
# created_or_detected_at: Unknown
# owner: Unknown
# <<< l9:meta <<<
from .syncer import sync_graph_from_index

__all__ = ["sync_graph_from_index"]
