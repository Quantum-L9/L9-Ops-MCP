# --- L9_META ---
# l9_schema: 1
# component: library_health
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

#!/usr/bin/env python3
"""
library_health.py — L9 Pack library health check.
Detects: stale last_tested dates, missing retrieval_keys, missing tier markers,
missing production_ready, and files whose metadata is absent or unparseable.
Scans docs/kernels, skills and docs/profiles under --root (default: the
repository root, independent of the working directory).
Exits 1 when issues are found or when no files were scanned.
"""

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from validate_helpers import ROOT, MetadataError, load_metadata

SEARCH_DIRS = ("docs/kernels", "skills", "docs/profiles")


def _as_date(value):
    """Coerce a YAML date/datetime/ISO string to a date; None when not a date."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def check_file(filepath, stale_days, today=None):
    today = today or date.today()
    try:
        meta = load_metadata(Path(filepath))
    except (MetadataError, UnicodeDecodeError) as exc:
        return [f"UNPARSEABLE metadata: {filepath} ({exc})"]
    if not isinstance(meta, dict):
        return [f"MISSING metadata: {filepath}"]

    issues = []
    raw = meta.get("last_tested") or meta.get("created")
    if raw:
        tested = _as_date(raw)
        if tested is None:
            issues.append(f"INVALID last_tested: {filepath} ({raw!r})")
        elif today - tested > timedelta(days=stale_days):
            issues.append(f"STALE: {filepath} (last_tested: {tested.isoformat()})")

    if not meta.get("retrieval_keys"):
        issues.append(f"MISSING retrieval_keys: {filepath}")
    if not meta.get("ring"):
        issues.append(f"MISSING ring: {filepath}")
    if meta.get("production_ready") is None:
        issues.append(f"MISSING production_ready: {filepath}")
    return issues


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT), help="library root (default: repository)")
    parser.add_argument("--stale-days", type=int, default=90)
    parser.add_argument("--check-eval-coverage", action="store_true")
    parser.add_argument("--check-tier-markers", action="store_true")
    parser.add_argument("--check-missing-retrieval-keys", action="store_true")
    parser.add_argument("--report", default="health_report.md")
    args = parser.parse_args()

    root = Path(args.root)
    all_issues = []
    scanned = 0
    for search_dir in SEARCH_DIRS:
        base = root / search_dir
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix in (".yaml", ".md"):
                scanned += 1
                all_issues.extend(check_file(path, args.stale_days))

    print(f"  scanned {scanned} files under {root}")
    if scanned == 0:
        all_issues.append(f"NO INPUT: none of {', '.join(SEARCH_DIRS)} has files under {root}")

    with open(args.report, "w") as f:
        f.write("# Library Health Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        if all_issues:
            f.write(f"## Issues Found ({len(all_issues)})\n\n")
            for issue in all_issues:
                f.write(f"- {issue}\n")
        else:
            f.write("## All Clear — No Issues Found\n")

    if all_issues:
        print(f"  {len(all_issues)} issues found — see {args.report}")
        return 1
    print("  Library health: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
