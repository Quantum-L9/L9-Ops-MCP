# --- L9_META ---
# l9_schema: 1
# component: validate-protected-files-v6
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

#!/usr/bin/env python3
"""
L9 Protected Files Validator v6.0.0

Fail-closed CI gate that blocks PR merges modifying protected files
without explicit approval (label or commit message token).

Usage (CI):
    PR_LABELS="LCTO_APPROVED,bug" python scripts/validate-protected-files-v6.py

Usage (local dry-run):
    python scripts/validate-protected-files-v6.py --dry-run [--base-ref origin/develop]

DORA:
    component_id: PFV-OPS-001
    tier: operations
    lifecycle: production
    owner: LCTO
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Protected Files Validator V6",
    "module_version": "6.0.0",
    "created_by": "L11 Governance Pipeline",
    "created_at": "2026-02-15T18:00:00Z",
    "updated_at": "2026-02-15T18:00:00Z",
    "layer": "operations",
    "domain": "governance",
    "module_name": "validate_protected_files_v6",
    "type": "validator",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from datetime import datetime, UTC
from pathlib import Path

try:
    import structlog

    logger = structlog.get_logger(__name__)
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


POLICY_PATH = Path("config/policies/protected_files.yaml")
REPORT_PATH = Path("protected_files_gate_report.json")


def load_policy() -> dict:
    """Load protected files policy. Fail-closed if missing."""
    try:
        import yaml
    except ImportError:
        logger.error("pyyaml not installed — fail closed")
        sys.exit(1)

    if not POLICY_PATH.exists():
        logger.error(
            "policy_file_missing",
            path=str(POLICY_PATH),
            action="fail_closed",
        )
        sys.exit(1)

    try:
        with open(POLICY_PATH) as f:
            policy = yaml.safe_load(f)
        if not policy or "categories" not in policy:
            logger.error("policy_invalid", path=str(POLICY_PATH))
            sys.exit(1)
        return policy
    except Exception as e:
        logger.error("policy_load_failed", error=str(e))
        sys.exit(1)


class ChangeSetError(RuntimeError):
    """The PR change set could not be computed; the gate must fail closed."""


def get_changed_files(base_ref: str = "origin/main") -> list[str]:
    """Return every path changed by the PR (``base_ref...HEAD``).

    Fail-closed: if git cannot compute the change set (missing/unfetched base
    ref, no merge base, git unavailable) this raises ``ChangeSetError`` instead
    of returning an empty list. Rename detection is disabled so that both the
    old and the new path of a renamed file are reported, and no diff filter is
    applied so deletions and type changes are reported too.
    """
    cmd = [
        "git",
        "diff",
        "--name-only",
        "--no-renames",
        "-z",
        "--end-of-options",
        f"{base_ref}...HEAD",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        raise ChangeSetError(f"git diff {base_ref}...HEAD could not run: {e}") from e
    if result.returncode != 0:
        detail = result.stderr.strip() or "no stderr"
        raise ChangeSetError(
            f"git diff {base_ref}...HEAD failed (exit {result.returncode}): {detail}"
        )
    return [f for f in result.stdout.split("\0") if f]


def get_all_protected_paths(policy: dict) -> list[str]:
    """Extract all protected path patterns from policy."""
    paths = []
    categories = policy.get("categories", {})

    lcto = categories.get("lcto_controlled", {})
    paths.extend(lcto.get("protected_paths", []))

    subsystems = categories.get("subsystem_protected", {}).get("subsystems", {})
    for _name, sub in subsystems.items():
        paths.extend(sub.get("protected_paths", []))

    return paths


def get_meta_protected_files(policy: dict) -> list[str]:
    """Get meta-protected files (self-protecting)."""
    return policy.get("meta_protected_files", [])


def file_matches_pattern(filepath: str, pattern: str) -> bool:
    """Check if filepath matches a glob pattern."""
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return filepath.startswith(prefix)
    return fnmatch.fnmatch(filepath, pattern)


def get_approval_signals(policy: dict) -> tuple[list[str], list[str]]:
    """Get approval label names and commit message tokens."""
    signals = policy.get("approval_signals", {})
    labels = signals.get("pr_labels", ["LCTO_APPROVED", "IGOR_APPROVED"])
    tokens = signals.get("commit_message_tokens", ["HIL_APPROVED", "IGOR_APPROVED"])
    return labels, tokens


def check_approval(policy: dict, base_ref: str = "origin/main") -> bool:
    """Check if PR has approval signal (label or commit message token).

    Commit tokens are read only from commits reachable from HEAD and not from
    ``base_ref`` (``base_ref..HEAD``), i.e. the PR's own commits. If the log
    cannot be read, no commit approval is granted (fail closed).
    """
    labels_allowed, tokens_allowed = get_approval_signals(policy)

    # Check PR labels (from GitHub Actions env)
    pr_labels_raw = os.environ.get("PR_LABELS", "")
    pr_labels = [label.strip() for label in pr_labels_raw.split(",") if label.strip()]
    for label in pr_labels:
        if label in labels_allowed:
            logger.info("approval_found", signal_type="pr_label", signal=label)
            return True

    # Check commit messages of the PR's own commits only
    try:
        result = subprocess.run(
            ["git", "log", "--format=%s", "--end-of-options", f"{base_ref}..HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as e:
        logger.error("git_log_failed", error=str(e), action="no_commit_approval")
        return False
    if result.returncode != 0:
        logger.error(
            "git_log_failed",
            error=result.stderr.strip(),
            action="no_commit_approval",
        )
        return False
    for line in result.stdout.strip().split("\n"):
        for token in tokens_allowed:
            if token in line:
                logger.info("approval_found", signal_type="commit_msg", signal=token)
                return True

    return False


def _check_base_ref(base_ref: str) -> None:
    """Reject a base ref git would parse as an option (e.g. ``--output=<path>``)."""
    if not base_ref or base_ref.startswith("-"):
        raise ChangeSetError(f"invalid base ref {base_ref!r}: must name a revision")


def _first_match(filepath: str, patterns: list[str], category: str) -> dict | None:
    """Return the violation record for the first pattern ``filepath`` matches."""
    for pattern in patterns:
        if file_matches_pattern(filepath, pattern):
            return {
                "file": filepath,
                "matched_pattern": pattern,
                "category": category,
                "timestamp": datetime.now(UTC).isoformat(),
            }
    return None


def _find_violations(
    changed_files: list[str],
    protected_patterns: list[str],
    meta_patterns: list[str],
) -> tuple[list[dict], list[dict]]:
    """Split changed files into protected and meta-protected violations."""
    violations: list[dict] = []
    meta_violations: list[dict] = []

    for filepath in changed_files:
        # Check protected paths
        violation = _first_match(filepath, protected_patterns, "protected")
        if violation is not None:
            violations.append(violation)

        # Check meta-protected (self-protecting files)
        meta_violation = _first_match(filepath, meta_patterns, "meta_protected")
        if meta_violation is not None:
            meta_violations.append(meta_violation)

    return violations, meta_violations


def _print_violation_banner(all_violations: list[dict]) -> None:
    """Print the blocking banner listing every unapproved violation."""
    print("\n" + "=" * 70)
    print("🛡️  PROTECTED FILES GATE — VIOLATION DETECTED")
    print("=" * 70)
    print(f"\n{len(all_violations)} protected file(s) modified without approval:\n")

    for v in all_violations:
        prefix = "🔴 META" if v["category"] == "meta_protected" else "🟡 PROTECTED"
        print(f"  {prefix}: {v['file']}")
        print(f"           Pattern: {v['matched_pattern']}")

    print("\n── How to fix ──")
    print("  Option A: Add PR label LCTO_APPROVED or IGOR_APPROVED")
    print("  Option B: Include HIL_APPROVED or IGOR_APPROVED in commit message")
    print("=" * 70 + "\n")


def validate(dry_run: bool = False, base_ref: str = "origin/main") -> int:
    """Main validation logic. Returns exit code (0=pass, 1=fail)."""
    policy = load_policy()
    try:
        _check_base_ref(base_ref)
        changed_files = get_changed_files(base_ref)
    except ChangeSetError as e:
        # Fail closed even in dry-run: without a change set there is no verdict.
        logger.error("change_set_unavailable", error=str(e), action="fail_closed")
        print(f"PROTECTED FILES GATE — cannot compute change set: {e}", file=sys.stderr)
        write_report([], [], False, "change_set_unavailable", error=str(e))
        return 1

    if not changed_files:
        logger.info("no_changed_files")
        write_report([], [], True, "no_changes")
        return 0

    violations, meta_violations = _find_violations(
        changed_files,
        get_all_protected_paths(policy),
        get_meta_protected_files(policy),
    )
    all_violations = violations + meta_violations

    if not all_violations:
        logger.info("no_protected_files_modified", changed_count=len(changed_files))
        write_report(changed_files, [], True, "no_violations")
        return 0

    # Check for approval
    has_approval = check_approval(policy, base_ref)

    if has_approval:
        logger.info(
            "protected_files_approved",
            violation_count=len(all_violations),
            meta_count=len(meta_violations),
        )
        write_report(changed_files, all_violations, True, "approved")
        return 0

    # No approval — BLOCK
    logger.error(
        "protected_files_violation",
        violation_count=len(all_violations),
        meta_count=len(meta_violations),
    )

    _print_violation_banner(all_violations)

    if dry_run:
        print("DRY RUN — would have blocked merge")
        write_report(changed_files, all_violations, False, "dry_run")
        return 0

    write_report(changed_files, all_violations, False, "blocked")
    return 1


def write_report(
    changed_files: list,
    violations: list,
    passed: bool,
    reason: str,
    error: str | None = None,
) -> None:
    """Write JSON audit report."""
    report: dict = {
        "gate": "protected_files_v6",
        "timestamp": datetime.now(UTC).isoformat(),
        "passed": passed,
        "reason": reason,
        "changed_files_count": len(changed_files),
        "violation_count": len(violations),
        "violations": violations,
        "commit_sha": os.environ.get("GITHUB_SHA", "local"),
        "actor": os.environ.get("GITHUB_ACTOR", "local"),
        "pr_labels": os.environ.get("PR_LABELS", ""),
    }
    if error is not None:
        report["error"] = error
    try:
        with open(REPORT_PATH, "w") as f:
            json.dump(report, f, indent=2)
        logger.info("report_written", path=str(REPORT_PATH))
    except Exception as e:
        logger.warning("report_write_failed", error=str(e))


def main() -> None:
    parser = argparse.ArgumentParser(description="L9 Protected Files Validator v6")
    parser.add_argument("--dry-run", action="store_true", help="Report only, do not fail")
    parser.add_argument(
        "--base-ref",
        default="origin/main",
        help="PR base revision (CI passes github.event.pull_request.base.sha)",
    )
    args = parser.parse_args()
    sys.exit(validate(dry_run=args.dry_run, base_ref=args.base_ref))


if __name__ == "__main__":
    main()
