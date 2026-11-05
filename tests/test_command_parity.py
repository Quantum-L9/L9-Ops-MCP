# --- L9_META ---
# l9_schema: 1
# artifact_type: test
# tags: [ci-proof, command-parity]
# retrieval: on_demand
# status: active
# --- /L9_META ---

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import validate_command_parity as parity
from scripts.validate_helpers import extract_make_targets, read_makefile_tree


def test_included_repository_commands_are_not_missing(tmp_path: Path) -> None:
    (tmp_path / "Makefile").write_text("include Repo.mk\nsetup: repo-setup\n")
    (tmp_path / "Repo.mk").write_text("repo-setup:\n\techo setup\nhealth wiring:\n\techo check\n")
    targets = extract_make_targets(read_makefile_tree(tmp_path / "Makefile"))
    assert {"setup", "repo-setup", "health", "wiring"} <= targets


@pytest.mark.parametrize("include", ["Repo.mk", "$(shell touch ran)", "*.mk", "../outside.mk"])
def test_missing_dynamic_and_escaping_includes_fail(tmp_path: Path, include: str) -> None:
    (tmp_path / "Makefile").write_text(f"include {include}\n")
    with pytest.raises(ValueError):
        read_makefile_tree(tmp_path / "Makefile")
    assert not (tmp_path / "ran").exists()


def test_cyclic_include_fails(tmp_path: Path) -> None:
    (tmp_path / "Makefile").write_text("include Repo.mk\n")
    (tmp_path / "Repo.mk").write_text("include Makefile\n")
    with pytest.raises(ValueError, match="Cyclic"):
        read_makefile_tree(tmp_path / "Makefile")


def test_symlink_escape_fails(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "outside.mk"
    outside.write_text("health:\n\techo check\n")
    (root / "Makefile").write_text("include Repo.mk\n")
    (root / "Repo.mk").symlink_to(outside)
    with pytest.raises(ValueError, match="escapes"):
        read_makefile_tree(root / "Makefile")


def test_both_workflow_extensions_are_checked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(parity, "ROOT", tmp_path)
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "a.yml").write_text("run: make validate\n")
    (workflows / "b.yaml").write_text("run: make test\n")
    assert parity.workflow_commands() == {"validate", "test"}


def test_unknown_advertised_command_blocks_parity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(parity, "ROOT", tmp_path)
    (tmp_path / "Makefile").write_text("include Repo.mk\n")
    (tmp_path / "Repo.mk").write_text("health:\n\techo check\n")
    (tmp_path / "README.md").write_text("make missing-command\n")
    assert parity.main() == 1


def test_real_repo_parity_passes_from_any_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert parity.main() == 0
