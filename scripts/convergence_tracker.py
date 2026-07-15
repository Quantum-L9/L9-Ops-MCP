# --- L9_META ---
# l9_schema: 1
# component: convergence_tracker
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

#!/usr/bin/env python3
"""
l9-ops: Convergence Tracker (v1.2.2)
Reads convergence_footer from all optimized kernels. Reports eval/rot status.
Activates the dormant convergence_footer telemetry schema.

Usage:
  python3 scripts/convergence_tracker.py
  python3 scripts/convergence_tracker.py --rot-threshold-days 90
  python3 scripts/convergence_tracker.py --write-report
  python3 scripts/convergence_tracker.py --update-kernel context_budget_kernel.v1 --pass-rate 0.92 --model claude-sonnet-4
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

LIBRARY_ROOT = Path(__file__).parent.parent
KERNEL_DIR = LIBRARY_ROOT / "kernels" / "optimized"
REPORT_PATH = LIBRARY_ROOT / "evals" / "convergence-status.yaml"
TODAY = datetime.now().strftime("%Y-%m-%d")


def extract_footer(kpath):
    c = kpath.read_text()
    f = {
        "kernelid": None,
        "status": "unknown",
        "threshold": 0.05,
        "pass_count": 0,
        "final_ratio": 0.0,
        "lastRunDate": None,
        "modelVersion": None,
        "file": kpath.name,
    }
    m = re.search(r"^kernelid:\s*(.+)$", c, re.MULTILINE)
    if m:
        f["kernelid"] = m.group(1).strip()
    cf = re.search(r"convergence_footer:(.*)", c, re.DOTALL | re.IGNORECASE)
    if cf:
        block = cf.group(1)
        for field in [
            "status",
            "threshold",
            "pass_count",
            "final_ratio",
            "lastRunDate",
            "modelVersion",
        ]:
            fm = re.search(field + r":\s*(.+)", block)
            if fm:
                v = fm.group(1).strip()
                if v in ("null", "~", "", "[]"):
                    f[field] = None
                elif re.fullmatch(r"-?\d+\.\d+", v):
                    f[field] = float(v)
                elif re.fullmatch(r"-?\d+", v):
                    f[field] = int(v)
                else:
                    f[field] = v
    return f


def classify(footer, rot_days):
    if footer.get("lastRunDate") is None:
        return "NEVER_EVALUATED"
    try:
        last = datetime.strptime(str(footer["lastRunDate"]), "%Y-%m-%d")
        age = (datetime.now() - last).days
        if age > rot_days:
            return f"STALE({age}d)"
        if (footer.get("final_ratio") or 0.0) < (footer.get("threshold") or 0.05):
            return "BELOW_THRESHOLD"
        return "CURRENT"
    except (ValueError, TypeError):
        return "INVALID_DATE"


def report(rot_days):
    buckets = {"NEVER_EVALUATED": [], "STALE": [], "BELOW_THRESHOLD": [], "CURRENT": []}
    kernels = []
    for kf in sorted(KERNEL_DIR.glob("*.yaml")):
        f = extract_footer(kf)
        s = classify(f, rot_days)
        f["rot_status"] = s
        kernels.append(f)
        key = "STALE" if s.startswith("STALE") else s
        buckets.setdefault(key, []).append(f["kernelid"] or kf.name)
    return {
        "generated": TODAY,
        "rot_threshold_days": rot_days,
        "summary": {
            "total": len(kernels),
            "never_evaluated": len(buckets["NEVER_EVALUATED"]),
            "stale": len(buckets["STALE"]),
            "below_threshold": len(buckets["BELOW_THRESHOLD"]),
            "current": len(buckets["CURRENT"]),
        },
        "buckets": buckets,
        "kernels": kernels,
    }


def print_report(r):
    s = r["summary"]
    bar = "=" * 55
    print(
        f"\n{bar}\n  l9-ops Convergence Tracker\n  {r['generated']} | Rot threshold: {r['rot_threshold_days']}d\n{bar}"
    )
    print(f"  Total kernels:   {s['total']}")
    print(f"  Never evaluated: {s['never_evaluated']}  <- create eval fixtures + run evals")
    print(f"  Stale:           {s['stale']}")
    print(f"  Below threshold: {s['below_threshold']}")
    print(f"  Current:         {s['current']}")
    for status, ids in [
        ("NEVER EVALUATED", r["buckets"]["NEVER_EVALUATED"]),
        ("STALE", r["buckets"]["STALE"]),
        ("BELOW THRESHOLD", r["buckets"]["BELOW_THRESHOLD"]),
    ]:
        if ids:
            print(f"\n  {status}:")
            for k in ids:
                print(f"    -> {k}")
    print("\n  To collect evidence: npx promptfoo eval --config evals/promptfooconfig.yaml")


def update_kernel(kernel_id, pass_rate, model):
    target = None
    for f in KERNEL_DIR.glob("*.yaml"):
        if kernel_id in f.read_text():
            target = f
            break
    if not target:
        print(f"ERROR: kernel '{kernel_id}' not found", file=sys.stderr)
        sys.exit(1)
    status = "stable" if pass_rate >= 0.85 else ("converging" if pass_rate >= 0.5 else "diverging")
    lines = target.read_text().split("\n")
    in_footer = False
    out = []
    for line in lines:
        if re.search(r"convergence_footer:", line, re.IGNORECASE):
            in_footer = True
        if in_footer:
            if re.match(r"\s*final_ratio:", line):
                line = re.sub(r"final_ratio:.*", f"final_ratio: {round(pass_rate, 3)}", line)
            elif re.match(r"\s*status:", line):
                line = re.sub(r"status:.*", f"status: {status}", line)
            elif re.match(r"\s*lastRunDate:", line):
                line = re.sub(r"lastRunDate:.*", f"lastRunDate: {TODAY}", line)
            elif re.match(r"\s*modelVersion:", line):
                line = re.sub(r"modelVersion:.*", f"modelVersion: {model}", line)
        out.append(line)
    target.write_text("\n".join(out))
    print(
        f"OK updated {kernel_id}: status={status} final_ratio={pass_rate:.3f} lastRunDate={TODAY} modelVersion={model}"
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rot-threshold-days", type=int, default=90)
    p.add_argument("--update-kernel")
    p.add_argument("--pass-rate", type=float)
    p.add_argument("--model", default="claude-sonnet-4")
    p.add_argument("--write-report", action="store_true")
    a = p.parse_args()
    if a.update_kernel:
        if a.pass_rate is None:
            print("ERROR: --pass-rate required", file=sys.stderr)
            sys.exit(1)
        update_kernel(a.update_kernel, a.pass_rate, a.model)
        return
    r = report(a.rot_threshold_days)
    print_report(r)
    if a.write_report:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(f"# l9-ops Convergence Status\n# Generated: {r['generated']}\n\n")
        print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
