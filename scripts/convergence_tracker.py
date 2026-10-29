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
Reads convergence_footer from every YAML kernel under docs/kernels.
Reports eval/rot status; exits 1 when no kernel is found.
Activates the dormant convergence_footer telemetry schema.

--update-kernel selects the kernel whose parsed kernel_id equals the argument
and edits only the direct child keys of that file's top-level
convergence_footer block (missing keys are appended to the block). The edited
text is re-parsed and verified before it is written.

Usage:
  python3 scripts/convergence_tracker.py
  python3 scripts/convergence_tracker.py --rot-threshold-days 90
  python3 scripts/convergence_tracker.py --write-report
  python3 scripts/convergence_tracker.py --update-kernel context_budget_kernel.v1 --pass-rate 0.92 --model claude-sonnet-4
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

LIBRARY_ROOT = Path(__file__).parent.parent
KERNEL_DIR = LIBRARY_ROOT / "docs" / "kernels"
REPORT_PATH = LIBRARY_ROOT / "evals" / "convergence-status.yaml"
TODAY = datetime.now().strftime("%Y-%m-%d")

FOOTER_KEY = "convergence_footer"
FOOTER_FIELDS = ("status", "threshold", "pass_count", "final_ratio", "lastRunDate", "modelVersion")


class TrackerError(Exception):
    """A kernel could not be read, parsed, selected or safely edited."""


def _load_docs(kpath: Path) -> list[Any]:
    try:
        return list(yaml.safe_load_all(kpath.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        msg = f"{kpath}: cannot parse kernel YAML ({exc})"
        raise TrackerError(msg) from exc


def _kernel_doc(docs: list[Any]) -> dict[str, Any] | None:
    """Return the document that declares kernel_id (multi-document aware)."""
    for doc in docs:
        if isinstance(doc, dict) and isinstance(doc.get("kernel_id") or doc.get("kernelid"), str):
            return doc
    return None


def _scalar(value: Any) -> Any:
    if value in ("", [], "~"):
        return None
    if hasattr(value, "isoformat") and not isinstance(value, datetime):
        return value.isoformat()  # YAML dates -> "YYYY-MM-DD"
    return value


def extract_footer(kpath: Path) -> dict[str, Any] | None:
    """Return footer telemetry for a kernel file, or None if it is not a kernel."""
    doc = _kernel_doc(_load_docs(kpath))
    if doc is None:
        return None
    f: dict[str, Any] = {
        "kernelid": doc.get("kernel_id") or doc.get("kernelid"),
        "status": "unknown",
        "threshold": 0.05,
        "pass_count": 0,
        "final_ratio": 0.0,
        "lastRunDate": None,
        "modelVersion": None,
        "file": kpath.name,
    }
    footer = doc.get(FOOTER_KEY)
    if isinstance(footer, dict):
        for field in FOOTER_FIELDS:
            if field in footer:
                f[field] = _scalar(footer[field])
    return f


def iter_kernel_files() -> list[Path]:
    return sorted(p for p in KERNEL_DIR.rglob("*.yaml") if p.is_file())


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
    for kf in iter_kernel_files():
        f = extract_footer(kf)
        if f is None:
            continue  # YAML under docs/kernels without a kernel_id is not a kernel
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


def _find_kernel(kernel_id: str) -> Path:
    matches = []
    for kf in iter_kernel_files():
        doc = _kernel_doc(_load_docs(kf))
        if doc is not None and (doc.get("kernel_id") or doc.get("kernelid")) == kernel_id:
            matches.append(kf)
    if not matches:
        msg = f"kernel '{kernel_id}' not found under {KERNEL_DIR}"
        raise TrackerError(msg)
    if len(matches) > 1:
        msg = f"kernel '{kernel_id}' declared by several files: {[str(m) for m in matches]}"
        raise TrackerError(msg)
    target = matches[0]
    if not target.resolve().is_relative_to(KERNEL_DIR.resolve()):
        msg = f"kernel '{kernel_id}' resolves outside {KERNEL_DIR}: {target.resolve()}"
        raise TrackerError(msg)
    return target


def _footer_bounds(lines: list[str]) -> tuple[int, int]:
    """Return [start, end) of the top-level convergence_footer block body."""
    header = [i for i, line in enumerate(lines) if re.match(rf"{FOOTER_KEY}:\s*(#.*)?$", line)]
    if len(header) != 1:
        msg = f"expected exactly one top-level '{FOOTER_KEY}:' block, found {len(header)}"
        raise TrackerError(msg)
    start = header[0] + 1
    end = start
    for i in range(start, len(lines)):
        line = lines[i]
        if line.strip() and not line[0].isspace():
            break  # next top-level key, comment or document marker ends the block
        end = i + 1
    while end > start and not lines[end - 1].strip():
        end -= 1  # keep trailing blank lines outside the block
    return start, end


def update_footer_text(text: str, updates: dict[str, str]) -> str:
    """Set ``updates`` (key -> YAML scalar text) as direct children of the footer."""
    lines = text.split("\n")
    start, end = _footer_bounds(lines)
    child_indent = None
    for line in lines[start:end]:
        if line.strip() and not line.lstrip().startswith("#"):
            child_indent = line[: len(line) - len(line.lstrip())]
            break
    if not child_indent:
        msg = f"'{FOOTER_KEY}' block has no child keys"
        raise TrackerError(msg)
    remaining = dict(updates)
    for i in range(start, end):
        m = re.match(rf"^{re.escape(child_indent)}([A-Za-z_][A-Za-z0-9_]*):(\s.*)?$", lines[i])
        if m and m.group(1) in remaining:
            lines[i] = f"{child_indent}{m.group(1)}: {remaining.pop(m.group(1))}"
    added = [f"{child_indent}{key}: {value}" for key, value in remaining.items()]
    lines[end:end] = added
    return "\n".join(lines)


def update_kernel(kernel_id, pass_rate, model):
    target = _find_kernel(kernel_id)
    status = "stable" if pass_rate >= 0.85 else ("converging" if pass_rate >= 0.5 else "diverging")
    ratio = round(pass_rate, 3)
    original = target.read_text(encoding="utf-8")
    updates = {
        "final_ratio": repr(float(ratio)),
        "status": status,
        "lastRunDate": TODAY,
        "modelVersion": json.dumps(model),
    }
    new_text = update_footer_text(original, updates)

    # Verify before writing: same documents except the four footer fields.
    before_doc = _kernel_doc(_load_docs(target))
    try:
        after_docs = list(yaml.safe_load_all(new_text))
    except yaml.YAMLError as exc:
        msg = f"{target}: edit would produce invalid YAML ({exc}); file left unchanged"
        raise TrackerError(msg) from exc
    after_doc = _kernel_doc(after_docs)
    expected = dict(before_doc or {})
    expected[FOOTER_KEY] = {
        **(before_doc or {}).get(FOOTER_KEY, {}),
        "final_ratio": float(ratio),
        "status": status,
        "lastRunDate": datetime.strptime(TODAY, "%Y-%m-%d").date(),
        "modelVersion": model,
    }
    if after_doc != expected:
        msg = f"{target}: edit verification failed; file left unchanged"
        raise TrackerError(msg)

    target.write_text(new_text, encoding="utf-8")
    print(
        f"OK updated {kernel_id} ({target}): status={status} final_ratio={pass_rate:.3f} "
        f"lastRunDate={TODAY} modelVersion={model}"
    )


def write_report(r: dict[str, Any]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    header = f"# l9-ops Convergence Status\n# Generated: {r['generated']}\n\n"
    REPORT_PATH.write_text(header + yaml.safe_dump(r, sort_keys=False), encoding="utf-8")
    print(f"Report: {REPORT_PATH}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rot-threshold-days", type=int, default=90)
    p.add_argument("--update-kernel")
    p.add_argument("--pass-rate", type=float)
    p.add_argument("--model", default="claude-sonnet-4")
    p.add_argument("--write-report", action="store_true")
    a = p.parse_args()
    try:
        if a.update_kernel:
            if a.pass_rate is None:
                print("ERROR: --pass-rate required", file=sys.stderr)
                return 1
            update_kernel(a.update_kernel, a.pass_rate, a.model)
            return 0
        r = report(a.rot_threshold_days)
    except TrackerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print_report(r)
    if a.write_report:
        write_report(r)
    if r["summary"]["total"] == 0:
        print(f"ERROR: no kernels found under {KERNEL_DIR}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
