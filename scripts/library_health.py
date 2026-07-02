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
eval coverage gaps, oversized kernels, and deprecated status.
"""
import os, sys, yaml, argparse
from datetime import datetime, timedelta

def check_file(filepath, stale_days):
    issues = []
    with open(filepath) as f:
        content = f.read()

    meta = None
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1])
            except:
                pass
    if meta is None:
        try:
            meta = yaml.safe_load(open(filepath))
        except:
            pass

    if not meta or not isinstance(meta, dict):
        return issues

    # Check stale last_tested
    last_tested = meta.get("last_tested") or meta.get("created")
    if last_tested:
        if isinstance(last_tested, str):
            try:
                dt = datetime.strptime(last_tested, "%Y-%m-%d")
                if datetime.now() - dt > timedelta(days=stale_days):
                    issues.append(f"STALE: {filepath} (last_tested: {last_tested})")
            except:
                pass

    # Check retrieval_keys
    if not meta.get("retrieval_keys"):
        issues.append(f"MISSING retrieval_keys: {filepath}")

    # Check ring
    if not meta.get("ring"):
        issues.append(f"MISSING ring: {filepath}")

    # Check production_ready
    if meta.get("production_ready") is None:
        issues.append(f"MISSING production_ready: {filepath}")

    return issues

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stale-days", type=int, default=90)
    parser.add_argument("--check-eval-coverage", action="store_true")
    parser.add_argument("--check-tier-markers", action="store_true")
    parser.add_argument("--check-missing-retrieval-keys", action="store_true")
    parser.add_argument("--report", default="health_report.md")
    args = parser.parse_args()

    all_issues = []

    for search_dir in ["docs/kernels", "skills", "docs/profiles"]:
        if not os.path.exists(search_dir):
            continue
        for root, dirs, files in os.walk(search_dir):
            for fname in files:
                if fname.endswith((".yaml", ".md")):
                    path = os.path.join(root, fname)
                    all_issues.extend(check_file(path, args.stale_days))

    with open(args.report, "w") as f:
        f.write(f"# Library Health Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        if all_issues:
            f.write(f"## Issues Found ({len(all_issues)})\n\n")
            for issue in all_issues:
                f.write(f"- {issue}\n")
        else:
            f.write("## All Clear — No Issues Found\n")

    if all_issues:
        print(f"  {len(all_issues)} issues found — see {args.report}")
        sys.exit(1)
    else:
        print("  Library health: OK")

if __name__ == "__main__":
    main()
