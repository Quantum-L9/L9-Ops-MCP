# --- L9_META ---
# l9_schema: 1
# component: impact_analysis
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

#!/usr/bin/env python3
"""
l9-ops: Impact Analysis (v1.2.2)
Answers: "If I change kernel X, what breaks?"
Uses MANIFEST.json file-path lookup — never fragile string munging.
"""
import argparse, json, sys
from pathlib import Path

LIBRARY_ROOT = Path(__file__).parent.parent


def load_manifest():
    return json.loads((LIBRARY_ROOT / "MANIFEST.json").read_text())


def build_reverse(manifest):
    reverse = {}
    dg = manifest.get("dependencyGraph", {})
    for skill, kernels in dg.get("skillsRequiringKernels", {}).items():
        for k in kernels:
            reverse.setdefault(k, {"skills": [], "playbooks": []})["skills"].append(skill)
    for pb, kernels in dg.get("playbookKernelRequirements", {}).items():
        for k in kernels:
            reverse.setdefault(k, {"skills": [], "playbooks": []})["playbooks"].append(pb)
    return reverse


def analyze(kid, manifest, reverse):
    deps = reverse.get(kid, {"skills": [], "playbooks": []})
    total = len(deps["skills"]) + len(deps["playbooks"])
    risk = "HIGH" if total >= 3 else ("MEDIUM" if total >= 1 else "LOW")
    entry = next((k for k in manifest.get("kernels", {}).get("registry", []) if k["id"] == kid), {})
    return {"kernel_id": kid, "risk": risk, "total": total,
            "skills": deps["skills"], "playbooks": deps["playbooks"],
            "eval_status": entry.get("evalStatus", "unknown")}


def print_analysis(r):
    bar = "=" * 55
    print(f"\n{bar}\n  Impact Analysis: {r['kernel_id']}\n  Risk: {r['risk']} | Impacted: {r['total']}\n{bar}")
    if r["skills"]:
        print("  Skills:")
        for s in r["skills"]: print(f"    -> {s}")
    else:
        print("  Skills: none")
    if r["playbooks"]:
        print("  Playbooks:")
        for pb in r["playbooks"]: print(f"    -> {pb}")
    else:
        print("  Playbooks: none")
    if r["eval_status"] == "untested":
        print(f"  Note: kernel '{r['kernel_id']}' is untested — run evals before this change")


def resolve_file_to_id(changed_path, manifest):
    """Use MANIFEST registry file-path lookup — never string munging."""
    changed = changed_path.replace("\\", "/")
    for k in manifest.get("kernels", {}).get("registry", []):
        if k.get("file") and (changed.endswith(k["file"]) or k["file"].endswith(Path(changed).name)):
            return k["id"]
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--all", action="store_true")
    p.add_argument("--kernel-id")
    p.add_argument("--changed", help="File path — resolved via MANIFEST file-path lookup")
    a = p.parse_args()

    manifest = load_manifest()
    reverse = build_reverse(manifest)
    kernel_ids = [k["id"] for k in manifest.get("kernels", {}).get("registry", [])]

    if a.all:
        for kid in kernel_ids:
            print_analysis(analyze(kid, manifest, reverse))
    elif a.kernel_id:
        if a.kernel_id not in kernel_ids:
            print(f"ERROR: '{a.kernel_id}' not in MANIFEST kernels.registry", file=sys.stderr); sys.exit(1)
        print_analysis(analyze(a.kernel_id, manifest, reverse))
    elif a.changed:
        kid = resolve_file_to_id(a.changed, manifest)
        if not kid:
            print(f"ERROR: Cannot resolve '{a.changed}' to a kernel ID via MANIFEST.", file=sys.stderr)
            print("  Ensure file is registered in MANIFEST.json kernels.registry with a 'file' field.", file=sys.stderr)
            sys.exit(1)
        print_analysis(analyze(kid, manifest, reverse))
    else:
        p.print_help(); sys.exit(1)

if __name__ == "__main__":
    main()
