# --- L9_META ---
# l9_schema: 1
# artifact_type: code
# tags: [preflight, cli, packaging]
# retrieval: on_demand
# status: active
# --- /L9_META ---

"""Console entrypoint for the repository's existing eight-gate live preflight.

Import is side-effect free. Invocation runs the existing script, including its
explicit live Graphiti/Neo4j smoke checks; CI only verifies this entrypoint is
importable and callable. A wheel install outside a checkout must supply --repo.
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

_LOG = logging.getLogger(__name__)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the existing checkout preflight and preserve its failure exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repository checkout (auto-detected for an editable install)",
    )
    args = parser.parse_args(argv)
    root = args.repo.resolve()
    script = root / "scripts" / "preflight.sh"
    if not script.is_file():
        _LOG.error("BLOCKED: scripts/preflight.sh absent; supply a repository checkout with --repo")
        return 2
    environment = os.environ.copy()
    environment["PATH"] = (
        str(Path(sys.executable).parent) + os.pathsep + environment.get("PATH", "")
    )
    try:
        result = subprocess.run(["bash", str(script)], cwd=root, env=environment, check=False)
    except OSError as exc:
        _LOG.error("BLOCKED: cannot launch repository preflight: %s", exc)
        return 2
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
