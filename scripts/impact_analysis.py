# --- L9_META ---
# l9_schema: 1
# component: impact_analysis
# artifact_type: context
# tags: [validation, impact]
# retrieval: on_demand
# status: active
# --- /L9_META ---
"""Analyze declared dependencies in the actual repository or a typed legacy pack.

Impact is bounded to declarations, not prose guesses or runtime/eval guarantees.
Invalid authority, missing declared artifacts, and unknown dependencies fail closed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from .repo_structure import ROOT, StructureError, contained_path, load_repository
except ImportError:
    from repo_structure import ROOT, StructureError, contained_path, load_repository

LIBRARY_ROOT = ROOT


def load_manifest(root: Path = LIBRARY_ROOT, manifest: str | None = None) -> dict[str, Any]:
    """Compatibility view from real authority, never config/MANIFEST fallback."""
    repository = load_repository(root, manifest)
    if repository.failures:
        raise StructureError(
            "invalid declared wiring:\n"
            + "\n".join(finding.line() for finding in repository.failures)
        )
    return repository.as_manifest()


def build_reverse(manifest: dict[str, Any]) -> dict[str, dict[str, list[str]]]:
    registries = {}
    for kind in ("kernel", "skill", "playbook", "prompt"):
        section = manifest.get(f"{kind}s", {})
        if not isinstance(section, dict) or not isinstance(section.get("registry", []), list):
            raise StructureError(f"malformed {kind} registry")
        for entry in section.get("registry", []):
            if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
                raise StructureError(f"malformed {kind} registry entry")
            if entry["id"] in registries:
                raise StructureError(f"duplicate artifact ID: {entry['id']}")
            registries[entry["id"]] = kind
    if not any(kind == "kernel" for kind in registries.values()):
        raise StructureError("empty/unknown manifest kernel registry")
    edges = manifest.get("declaredDependencies")
    if edges is None:
        graph = manifest.get("dependencyGraph", {})
        if not isinstance(graph, dict):
            raise StructureError("malformed dependencyGraph")
        if set(graph) - {"skillsRequiringKernels", "playbookKernelRequirements"}:
            raise StructureError("unknown dependencyGraph fields")
        edges = {}
        for field_name in ("skillsRequiringKernels", "playbookKernelRequirements"):
            rows = graph.get(field_name, {})
            if not isinstance(rows, dict):
                raise StructureError(f"malformed dependencyGraph.{field_name}")
            for source, targets in rows.items():
                if not isinstance(targets, list):
                    raise StructureError(f"malformed dependency list: {source}")
                edges.setdefault(source, []).extend(targets)
    if not isinstance(edges, dict):
        raise StructureError("malformed declaredDependencies")
    reverse: dict[str, dict[str, list[str]]] = {}
    for source, targets in edges.items():
        if source not in registries or not isinstance(targets, list):
            raise StructureError(f"unknown source/malformed dependencies: {source}")
        for target in targets:
            if not isinstance(target, str) or target not in registries:
                raise StructureError(f"unknown dependency: {source} -> {target}")
            bucket = reverse.setdefault(
                target, {f"{k}s": [] for k in ("kernel", "skill", "playbook", "prompt")}
            )
            bucket[f"{registries[source]}s"].append(source)
    return reverse


def analyze(
    kid: str, manifest: dict[str, Any], reverse: dict[str, dict[str, list[str]]]
) -> dict[str, Any]:
    entry = next(
        (k for k in manifest.get("kernels", {}).get("registry", []) if k["id"] == kid), None
    )
    if entry is None:
        raise StructureError(f"unknown kernel ID: {kid}")
    impacted: dict[str, set[str]] = {
        f"{k}s": set() for k in ("kernel", "skill", "playbook", "prompt")
    }
    seen = {kid}
    queue = [kid]
    while queue:
        target = queue.pop()
        for kind, sources in reverse.get(target, {}).items():
            for source in sources:
                if source in seen:
                    continue
                seen.add(source)
                impacted[kind].add(source)
                queue.append(source)
    total = sum(map(len, impacted.values()))
    return {
        "kernel_id": kid,
        "file": entry.get("file"),
        "risk": "HIGH" if total >= 3 else ("MEDIUM" if total else "UNKNOWN"),
        "total": total,
        **{kind: sorted(ids) for kind, ids in impacted.items()},
        "eval_status": entry.get("evalStatus", "unknown"),
        "coverage": "declared direct and transitive dependencies only; not runtime/eval assurance",
    }


def print_analysis(result: dict[str, Any]) -> None:
    print(f"\nImpact Analysis: {result['kernel_id']} ({result['file']})")
    print(f"Declared impact risk: {result['risk']} | Impacted: {result['total']}")
    for kind in ("kernels", "skills", "playbooks", "prompts"):
        print(f"  {kind}: {', '.join(result[kind]) or 'none declared'}")
    print(f"  Coverage: {result['coverage']}")
    print(f"  Eval status: {result['eval_status']} (not evaluated here)")


def resolve_file_to_id(changed_path: str, manifest: dict[str, Any]) -> str | None:
    """Exact contained registry path match, never suffix/basename matching."""
    root = Path(manifest.get("root", LIBRARY_ROOT)).resolve()
    supplied = Path(changed_path)
    if supplied.is_absolute():
        normalized = supplied.resolve()
        if not normalized.is_relative_to(root):
            raise StructureError(f"changed path escapes repository: {changed_path}")
    else:
        normalized = contained_path(root, changed_path)
    for kernel in manifest.get("kernels", {}).get("registry", []):
        if kernel.get("file") and contained_path(root, kernel["file"]) == normalized:
            return kernel["id"]
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--all", action="store_true")
    selection.add_argument("--kernel-id", "--id", dest="kernel_id")
    selection.add_argument("--changed", help="exact canonical kernel path (relative to repository)")
    parser.add_argument("--root", type=Path, default=LIBRARY_ROOT)
    parser.add_argument("--manifest", help="explicit contained legacy manifest path")
    parser.add_argument("--json", action="store_true", help="machine-readable declared impact")
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(args.root, args.manifest)
        reverse = build_reverse(manifest)
        kernel_ids = [k["id"] for k in manifest["kernels"]["registry"]]
        if args.kernel_id:
            kernel_ids = [args.kernel_id]
        elif args.changed:
            kid = resolve_file_to_id(args.changed, manifest)
            if kid is None:
                raise StructureError(f"cannot resolve exact registered kernel path: {args.changed}")
            kernel_ids = [kid]
        results = [analyze(kid, manifest, reverse) for kid in kernel_ids]
        if args.json:
            print(
                json.dumps(
                    {
                        "source": manifest["source"],
                        "artifacts_checked": sum(
                            len(manifest[f"{kind}s"]["registry"])
                            for kind in ("kernel", "skill", "playbook", "prompt")
                        ),
                        "results": results,
                    },
                    indent=2,
                )
            )
        else:
            print(f"Source: {manifest['source']}; kernels checked: {len(results)}")
            for result in results:
                print_analysis(result)
        return 0
    except Exception as exc:
        print(f"FAIL: impact-analysis: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
