# Apply Instructions

The GitHub connector could read the repo and PRs, but write attempts to the PR branch returned `Resource not accessible by integration`, and branch creation was blocked. Apply this pack with a local checkout or Codex.

## Recommended Application

```bash
git clone https://github.com/Quantum-L9/L9-Ops-MCP.git
cd L9-Ops-MCP
git checkout -b build/mcp-context-control-plane-proof-gates
cp -R /path/to/l9_ops_mcp_build_pack/. .
chmod +x scripts/*.sh scripts/*.py
python3 -m compileall scripts
make ci
git add .
git commit -m "feat(governance): add MCP context control plane proof gates"
git push -u origin build/mcp-context-control-plane-proof-gates
```

## PR Handling

1. Open a new PR from `build/mcp-context-control-plane-proof-gates` to `main`.
2. In the PR body, state that it consolidates the governance/proof layer required before PR #2/#3 merge.
3. Do not close PR #2 until the consolidation PR or PR #3 proves functional parity.
4. Close PR #2 as superseded only after parity evidence exists.
