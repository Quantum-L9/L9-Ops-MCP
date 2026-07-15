# --- L9_META ---
# l9_schema: 1
# component: 07-L11-AUTO-FIX-ENGINE
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

"""L11 Auto-Fix Engine.

Shadow-branch validation with rollback on test failure.
All auto-fix PRs require explicit HITL approval.

DORA:
    component_id: l11-auto-fix-engine
    tier: 3
    lifecycle: production
    owner: platform-engineering
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class FixResult:
    """Outcome of an auto-fix attempt."""

    success: bool
    finding_hash: str = ""
    fix_description: str = ""
    tests_passed: bool = False
    pr_url: str = ""
    reason: str = ""
    attempted_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "finding_hash": self.finding_hash,
            "fix_description": self.fix_description,
            "tests_passed": self.tests_passed,
            "pr_url": self.pr_url,
            "reason": self.reason,
            "attempted_at": self.attempted_at.isoformat(),
        }


class AutoFixEngine:
    """Auto-remediation with shadow validation and HITL gate.

    Safety pipeline:
      1. Create shadow branch
      2. Apply codemod/linter fix
      3. Run full test suite on shadow branch
      4. If tests fail → rollback, report failure
      5. If tests pass → create PR for human approval

    ADR Compliance:
        ADR-0019  structlog-only logging
        ADR-0055  Fail-loudly on critical errors
        ADR-0078  Explicit approval for destructive ops
    """

    SUPPORTED_CATEGORIES = frozenset(
        {
            "linting_errors",
            "import_sorting",
            "docstring_missing",
            "type_hint_missing",
            "structlog_migration",
        }
    )

    def __init__(self, config: dict[str, Any]) -> None:
        fix_cfg = config["remediation"]["auto_fix"]
        self.enabled: bool = fix_cfg.get("enabled", False)
        self.require_tests: bool = fix_cfg["safety"].get("require_passing_tests", True)
        self.shadow_diff: bool = fix_cfg["safety"].get("shadow_diff_validation", True)
        self.rollback: bool = fix_cfg["safety"].get("rollback_on_failure", True)
        self.require_approval: bool = fix_cfg["safety"].get("require_approval", True)

    # ── Public API ──────────────────────────
    async def attempt_fix(self, finding: dict[str, Any]) -> FixResult:
        """Attempt to auto-fix a single finding on a shadow branch.

        Returns a FixResult with success/failure details.
        """
        fhash = finding.get("finding_hash", finding.get("hash", "unknown"))

        if not self.enabled:
            return FixResult(
                success=False,
                finding_hash=fhash,
                reason="auto_fix_disabled",
            )

        category = finding.get("category", "")
        if category not in self.SUPPORTED_CATEGORIES:
            return FixResult(
                success=False,
                finding_hash=fhash,
                reason=f"unsupported_category:{category}",
            )

        shadow_branch = f"auto-fix/{fhash[:12]}"
        original_branch = self._current_branch()

        try:
            # Step 1: Create shadow branch
            self._git("checkout", "-b", shadow_branch)
            logger.info("shadow_branch_created", branch=shadow_branch)

            # Step 2: Apply fix
            fix_desc = self._apply_fix(finding)

            # Step 3: Stage + commit
            file_path = finding.get("file", "")
            if file_path:
                self._git("add", file_path)
            self._git(
                "commit",
                "-m",
                f"auto-fix: {finding.get('rule', 'unknown')} in {file_path}",
            )

            # Step 4: Run tests on shadow branch
            tests_passed = self._run_tests()

            if not tests_passed:
                # Step 4a: Rollback
                self._cleanup_branch(original_branch, shadow_branch)
                logger.warning(
                    "auto_fix_rolled_back",
                    reason="tests_failed",
                    branch=shadow_branch,
                )
                return FixResult(
                    success=False,
                    finding_hash=fhash,
                    fix_description=fix_desc,
                    tests_passed=False,
                    reason="tests_failed_on_shadow",
                )

            # Step 5: Push + create PR
            self._git("push", "origin", shadow_branch)
            pr_url = self._create_pr_url(shadow_branch, finding)

            logger.info(
                "auto_fix_pr_created",
                branch=shadow_branch,
                pr_url=pr_url,
            )

            # Return to original branch
            self._git("checkout", original_branch)

            return FixResult(
                success=True,
                finding_hash=fhash,
                fix_description=fix_desc,
                tests_passed=True,
                pr_url=pr_url,
            )

        except subprocess.CalledProcessError as exc:
            logger.error(
                "auto_fix_failed",
                error=str(exc),
                branch=shadow_branch,
            )
            self._cleanup_branch(original_branch, shadow_branch)
            return FixResult(
                success=False,
                finding_hash=fhash,
                reason=f"git_error:{exc}",
            )

    # ── Fix Strategies ──────────────────────
    def _apply_fix(self, finding: dict[str, Any]) -> str:
        """Apply the appropriate codemod for the finding category."""
        file_path = finding.get("file", "")
        category = finding.get("category", "")

        if category == "linting_errors":
            subprocess.run(
                ["ruff", "check", "--fix", file_path],
                check=True,
                capture_output=True,
            )
            return f"ruff --fix applied to {file_path}"

        if category == "import_sorting":
            subprocess.run(
                ["ruff", "check", "--select", "I", "--fix", file_path],
                check=True,
                capture_output=True,
            )
            return f"import sorting applied to {file_path}"

        if category == "structlog_migration":
            # Use L9 lint_forbidden_imports.py --fix
            subprocess.run(
                [
                    "python",
                    "ci/check_forbidden_imports.py",
                    "--fix",
                    file_path,
                ],
                check=True,
                capture_output=True,
            )
            return f"structlog migration applied to {file_path}"

        return f"no-op for category {category}"

    # ── Git Helpers ─────────────────────────
    @staticmethod
    def _git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            check=True,
            capture_output=True,
            text=True,
        )

    @staticmethod
    def _current_branch() -> str:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def _cleanup_branch(self, original: str, shadow: str) -> None:
        """Force-checkout original and delete shadow branch."""
        try:
            self._git("checkout", "-f", original)
            self._git("branch", "-D", shadow)
        except subprocess.CalledProcessError as exc:
            logger.error("cleanup_failed", error=str(exc))

    @staticmethod
    def _run_tests() -> bool:
        """Run pytest on the shadow branch."""
        result = subprocess.run(
            ["pytest", "tests/", "-x", "--tb=short", "-q"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    @staticmethod
    def _create_pr_url(branch: str, finding: dict[str, Any]) -> str:
        """Build the GitHub compare URL for PR creation."""
        repo = "cryptoxdog/L9"
        title = f"auto-fix: {finding.get('rule', 'unknown')}"
        return f"https://github.com/{repo}/compare/main...{branch}?expand=1&title={title}"
