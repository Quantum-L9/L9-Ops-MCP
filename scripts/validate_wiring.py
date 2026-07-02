# --- L9_META ---
# l9_schema: 1
# component: validate_wiring
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---

#!/usr/bin/env python3
"""
l9-ops: Wiring Validator (v1.2.2)
9-dimension check that every artifact is fully wired.

Usage:
  python3 scripts/validate_wiring.py           # all artifacts
  python3 scripts/validate_wiring.py --id X    # one artifact (auto-detect type)
  python3 scripts/validate_wiring.py --type kernel|skill|playbook|prompt

Exit: 0 = fully wired, 1 = gaps found
"""
import argparse, json, re, sys
from pathlib import Path

LIBRARY_ROOT = Path(__file__).parent.parent


def load():
    m = json.loads((LIBRARY_ROOT / "MANIFEST.json").read_text())
    a = (LIBRARY_ROOT / "AGENTS.md").read_text()
    pf_path = LIBRARY_ROOT / "evals" / "promptfooconfig.yaml"
    pf = pf_path.read_text() if pf_path.exists() else ""
    return m, a, pf


class R:
    def __init__(self):
        self.passes = []
        self.fails = []

    def ok(self, c, msg):  self.passes.append(f"  \u2713 [{c}] {msg}")
    def fail(self, c, msg, fix=None):
        e = f"  \u2717 [{c}] {msg}"
        if fix: e += f"\n    FIX: {fix}"
        self.fails.append(e)

    def print(self, aid):
        print(f"\n{'─'*55}\n  Wiring: {aid}")
        for l in self.passes: print(l)
        for l in self.fails:  print(l)
        status = "FULLY WIRED" if not self.fails else f"GAPS FOUND ({len(self.fails)})"
        print(f"  Status: {status}")
        return len(self.fails) == 0, self


def check_kernel(kid, m, agents, pf):
    r = R()
    reg = m.get("kernels", {}).get("registry", [])
    entry = next((k for k in reg if k.get("id") == kid), None)
    if not entry:
        r.fail("manifest", f"'{kid}' not in MANIFEST kernels.registry",
               f"python3 scripts/add_artifact.py kernel --id {kid} ...")
        return r.print(kid)
    r.ok("manifest", "In MANIFEST kernels.registry")

    fpath = LIBRARY_ROOT / entry.get("file", "")
    if not fpath.exists():
        r.fail("file", f"Not found: {entry.get('file')}")
    else:
        r.ok("file", f"Exists: {entry['file']}")
        c = fpath.read_text()
        if "Use when:" in c and "Signals:" in c:
            r.ok("trigger-triad", "Trigger Triad present")
        else:
            r.fail("trigger-triad", "Missing Use when:/Signals: in description",
                   "Fill per KERNEL_DOCTRINE.md §2.3")
        if "tier2_load:" in c and "tier3_load:" in c:
            r.ok("tiers", "Tier 2 and 3 markers present")
        else:
            r.fail("tiers", "Missing tier2_load or tier3_load",
                   "Add tier markers per KERNEL_DOCTRINE.md §3")
        if "lastRunDate:" in c:
            r.ok("convergence", "convergence_footer.lastRunDate present")
        else:
            r.fail("convergence", "Missing lastRunDate in convergence_footer",
                   "Add lastRunDate: null")
        stubs = re.findall(r'<[A-Z][^>]{3,}>', c)
        if not stubs:
            r.ok("authored", "No unfilled placeholders")
        else:
            r.fail("authored", f"Unfilled placeholders (warn, not blocking merge): {stubs[:2]}",
                   "Fill before marking eval-status: passing")

    if kid in agents:
        r.ok("agents-md", "In AGENTS.md")
    else:
        r.fail("agents-md", f"'{kid}' missing from AGENTS.md",
               "Add a row to the Kernels table")

    fixtures = list((LIBRARY_ROOT / "evals" / "datasets").glob(f"{kid}*.yaml"))
    if fixtures:
        r.ok("eval-fixture", f"Fixture: {fixtures[0].name}")
    else:
        r.fail("eval-fixture", f"No evals/datasets/{kid}*.yaml",
               f"Create evals/datasets/{kid}-basic.yaml")

    if kid in pf:
        r.ok("promptfoo", "In evals/promptfooconfig.yaml")
    else:
        r.fail("promptfoo", f"'{kid}' not in promptfooconfig.yaml",
               "Add a test block")

    return r.print(kid)


def check_skill(sid, m, agents, pf):
    r = R()
    reg = m.get("skills", {}).get("registry", [])
    entry = next((s for s in reg if s.get("id") == sid), None)
    if not entry:
        r.fail("manifest", f"'{sid}' not in MANIFEST skills.registry",
               f"python3 scripts/add_artifact.py skill --id {sid} ...")
        return r.print(sid)
    r.ok("manifest", "In MANIFEST skills.registry")

    fpath = LIBRARY_ROOT / entry.get("file", "")
    if not fpath.exists():
        r.fail("file", f"SKILL.md not found: {entry.get('file')}")
    else:
        r.ok("file", f"Exists: {entry['file']}")
        c = fpath.read_text()
        if "Use when:" in c and "Signals:" in c:
            r.ok("trigger-triad", "Trigger Triad present")
        else:
            r.fail("trigger-triad", "Missing Trigger Triad", "Fill per SKILLS_DOCTRINE.md §2.2")
        if "eval-status:" in c:
            r.ok("eval-status", "eval-status field present")
        else:
            r.fail("eval-status", "Missing eval-status in frontmatter")

        # Dep graph consistency
        mentioned = list(set(re.findall(r'([a-z][a-z0-9_]+kernel\.v\d+)', c)))
        dep_kernels = m.get("dependencyGraph", {}).get("skillsRequiringKernels", {}).get(sid, [])
        known_ids = {k["id"] for k in m.get("kernels", {}).get("registry", [])}
        for mk in mentioned:
            if mk in known_ids and mk not in dep_kernels:
                r.fail("dep-graph", f"Skill uses '{mk}' but not in dep graph",
                       f"Add '{mk}' to MANIFEST dependencyGraph.skillsRequiringKernels.{sid}")
            elif mk in known_ids:
                r.ok("dep-graph", f"Kernel dep '{mk}' wired")
        for dk in dep_kernels:
            if dk not in known_ids:
                r.fail("dep-graph-integrity", f"Dep graph ref '{dk}' not in kernels.registry")
            else:
                r.ok("dep-graph-integrity", f"Dep graph ref '{dk}' resolves")

    if sid in agents:
        r.ok("agents-md", "In AGENTS.md")
    else:
        r.fail("agents-md", f"'{sid}' not in AGENTS.md", "Add to Skills table")

    fixtures = list((LIBRARY_ROOT / "evals" / "datasets").glob(f"{sid}*.yaml"))
    if fixtures: r.ok("eval-fixture", f"Fixture: {fixtures[0].name}")
    else: r.fail("eval-fixture", f"No fixture for '{sid}'", f"Create evals/datasets/{sid}-basic.yaml")

    if sid in pf: r.ok("promptfoo", "In promptfooconfig.yaml")
    else: r.fail("promptfoo", f"'{sid}' not in promptfooconfig.yaml")

    return r.print(sid)


def check_playbook(pid, m, agents, pf):
    r = R()
    reg = m.get("playbooks", {}).get("registry", [])
    entry = next((p for p in reg if p.get("id") == pid), None)
    if not entry:
        r.fail("manifest", f"'{pid}' not in MANIFEST playbooks.registry",
               f"python3 scripts/add_artifact.py playbook --id {pid} ...")
        return r.print(pid)
    r.ok("manifest", "In MANIFEST playbooks.registry")

    fpath = LIBRARY_ROOT / entry.get("file", "")
    if fpath.exists():
        r.ok("file", f"Exists: {entry['file']}")
        c = fpath.read_text()
        if "Use when:" in c and "Signals:" in c:
            r.ok("trigger-triad", "Trigger Triad present")
        else:
            r.fail("trigger-triad", "Missing Trigger Triad", "Fill per PLAYBOOKS_DOCTRINE.md §2.2")
    else:
        r.fail("file", f"PLAYBOOK.md not found")

    pbdir = LIBRARY_ROOT / "playbooks" / pid
    if (pbdir / "steps").exists():   r.ok("dir-steps", "steps/ present")
    else: r.fail("dir-steps", "Missing steps/", f"mkdir playbooks/{pid}/steps/")
    if (pbdir / "data-types").exists(): r.ok("dir-dt", "data-types/ present")
    else: r.fail("dir-dt", "Missing data-types/", f"mkdir playbooks/{pid}/data-types/")

    dep_kernels = m.get("dependencyGraph", {}).get("playbookKernelRequirements", {}).get(pid, [])
    known_ids = {k["id"] for k in m.get("kernels", {}).get("registry", [])}
    for dk in dep_kernels:
        if dk not in known_ids:
            r.fail("dep-graph", f"'{dk}' not in kernels.registry")
        else:
            r.ok("dep-graph", f"Kernel ref '{dk}' resolves")

    if pid in agents: r.ok("agents-md", "In AGENTS.md")
    else: r.fail("agents-md", f"'{pid}' not in AGENTS.md")

    fixtures = list((LIBRARY_ROOT / "evals" / "datasets").glob(f"{pid}*.yaml"))
    if fixtures: r.ok("eval-fixture", f"Fixture: {fixtures[0].name}")
    else: r.fail("eval-fixture", f"No fixture for '{pid}'")

    return r.print(pid)


def check_prompt(pid, m, agents, pf):
    r = R()
    reg = m.get("prompts", {}).get("registry", [])
    entry = next((p for p in reg if p.get("id") == pid), None)
    if not entry:
        r.fail("manifest", f"'{pid}' not in MANIFEST prompts.registry")
        return r.print(pid)
    r.ok("manifest", "In MANIFEST prompts.registry")

    fpath = LIBRARY_ROOT / entry.get("file", "")
    if fpath.exists():
        r.ok("file", f"Exists: {entry['file']}")
        c = fpath.read_text()
        if "eval-status:" in c: r.ok("eval-status", "eval-status present")
        else: r.fail("eval-status", "Missing eval-status field")
    else:
        r.fail("file", f"File not found: {entry.get('file')}")

    fixtures = list((LIBRARY_ROOT / "evals" / "datasets").glob(f"{pid}*.yaml"))
    if fixtures: r.ok("eval-fixture", f"Fixture: {fixtures[0].name}")
    else: r.fail("eval-fixture", f"No fixture for '{pid}'", f"Create evals/datasets/{pid}-basic.yaml")

    return r.print(pid)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--id")
    p.add_argument("--type", choices=["kernel", "skill", "playbook", "prompt"])
    p.add_argument("--all", action="store_true")
    a = p.parse_args()
    if not a.id and not a.type and not a.all:
        a.all = True

    m, agents, pf = load()
    print("\nl9-ops Wiring Validator\n" + "=" * 55)

    total = total_gaps = 0

    def run(fn, aid):
        nonlocal total, total_gaps
        total += 1
        passed, rep = fn(aid, m, agents, pf)
        if not passed:
            total_gaps += len(rep.fails)

    if a.id:
        all_ids = (
            {k["id"]: check_kernel for k in m.get("kernels", {}).get("registry", [])} |
            {s["id"]: check_skill  for s in m.get("skills",  {}).get("registry", [])} |
            {pb["id"]: check_playbook for pb in m.get("playbooks", {}).get("registry", [])} |
            {pr["id"]: check_prompt for pr in m.get("prompts", {}).get("registry", [])}
        )
        if a.id in all_ids:
            run(all_ids[a.id], a.id)
        else:
            print(f"ERROR: '{a.id}' not found in any registry.", file=sys.stderr)
            sys.exit(1)
    else:
        if a.type in ("kernel",  None) or a.all:
            for k in m.get("kernels",  {}).get("registry", []): run(check_kernel,   k["id"])
        if a.type in ("skill",   None) or a.all:
            for s in m.get("skills",   {}).get("registry", []): run(check_skill,    s["id"])
        if a.type in ("playbook",None) or a.all:
            for pb in m.get("playbooks",{}).get("registry", []): run(check_playbook, pb["id"])
        if a.type in ("prompt",  None) or a.all:
            for pr in m.get("prompts",  {}).get("registry", []): run(check_prompt,   pr["id"])

    print("\n" + "=" * 55)
    print(f"  Artifacts checked: {total}")
    print(f"  Wiring gaps:       {total_gaps}")
    result = "ALL FULLY WIRED \u2713" if total_gaps == 0 else f"{total_gaps} WIRING GAPS — fix before merging"
    print(f"  Result: {result}")
    print("=" * 55)
    sys.exit(0 if total_gaps == 0 else 1)

if __name__ == "__main__":
    main()
