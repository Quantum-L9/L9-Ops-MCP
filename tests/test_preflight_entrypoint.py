# --- L9_META ---
# l9_schema: 1
# artifact_type: test
# tags: [preflight, cli, packaging]
# retrieval: on_demand
# status: active
# --- /L9_META ---

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from l9_ops_mcp import preflight


def test_missing_checkout_is_blocked_without_starting_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = Mock()
    monkeypatch.setattr(preflight.subprocess, "run", runner)
    assert preflight.main(["--repo", str(tmp_path)]) == 2
    runner.assert_not_called()


@pytest.mark.parametrize("exit_code", [0, 1, 17])
def test_delegates_to_real_script_and_preserves_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exit_code: int
) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    script = scripts / "preflight.sh"
    script.write_text("#!/usr/bin/env bash\nexit 0\n")
    runner = Mock(return_value=subprocess.CompletedProcess([], exit_code))
    monkeypatch.setattr(preflight.subprocess, "run", runner)
    assert preflight.main(["--repo", str(tmp_path)]) == exit_code
    args, kwargs = runner.call_args
    assert args == (["bash", str(script)],)
    assert kwargs["cwd"] == tmp_path
    assert kwargs["env"]["PATH"].split(os.pathsep)[0] == str(Path(sys.executable).parent)
    assert kwargs["check"] is False


def test_launch_failure_is_blocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "preflight.sh").write_text("#!/usr/bin/env bash\n")
    monkeypatch.setattr(preflight.subprocess, "run", Mock(side_effect=OSError("no bash")))
    assert preflight.main(["--repo", str(tmp_path)]) == 2
