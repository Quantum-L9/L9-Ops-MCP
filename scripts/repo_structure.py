# --- L9_META ---
# l9_schema: 1
# component: repository_structure
# artifact_type: context
# tags: [validation, wiring]
# retrieval: on_demand
# status: active
# --- /L9_META ---
"""Read-only structural inventory, shared by wiring and impact validation.

A root legacy MANIFEST is supported only if it has typed registries. Otherwise
this consolidated repository uses its real retrieval index and canonical runtime
registry. config/MANIFEST.json is an upstream provenance pack, never a fallback.
No content-eval success or inferred kernel dependencies are manufactured here.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
KINDS = ("kernel", "skill", "playbook", "prompt")
KERNEL_DEP_FIELDS = (
    "requires",
    "kernels_required",
    "required_kernels",
    "kernel-requirements",
    "kernel_requirements",
    "kernel_dependencies",
)
SKILL_DEP_FIELDS = ("skills_required", "required_skills", "skill-requirements")


class StructureError(ValueError):
    """Malformed authority or a reference outside the repository."""


def contained_path(root: Path, reference: str, base: Path | None = None) -> Path:
    if not isinstance(reference, str) or not reference.strip():
        raise StructureError("empty or non-string path reference")
    reference = unquote(reference).replace("\\", "/")
    if Path(reference).is_absolute() or re.match(r"^[A-Za-z]:", reference):
        raise StructureError(f"absolute path not permitted: {reference}")
    result = ((base or root) / reference).resolve()
    if not result.is_relative_to(root.resolve()):
        raise StructureError(f"path escapes repository: {reference}")
    return result


def read_mapping(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
        doc = json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        raise StructureError(f"cannot parse {path.name}: {exc}") from exc
    if not isinstance(doc, dict) or not doc:
        raise StructureError(f"{path.name}: expected nonempty mapping")
    return doc


def metadata_blocks(path: Path) -> list[dict[str, Any]]:
    """Read declarations only; prose/code examples are not dependencies."""
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        # Legacy YAML kernels may have a frontmatter document before the body.
        try:
            documents = list(yaml.safe_load_all(text))
        except yaml.YAMLError as exc:
            raise StructureError(f"malformed YAML artifact {path}: {exc}") from exc
        if not documents or any(not isinstance(doc, dict) or not doc for doc in documents):
            raise StructureError(f"YAML artifact {path} requires nonempty mapping documents")
        return documents
    blocks = []
    front = re.match(r"^---\s*\n(.*?)\n---(?:\s*\n|$)", text, re.S)
    raw_blocks = ([front.group(1)] if front else []) + re.findall(
        r"<!--\s*L9_META\s*\n(.*?)\n\s*/L9_META\s*-->", text, re.S
    )
    for raw in raw_blocks:
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            raise StructureError(f"malformed metadata in {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise StructureError(f"metadata in {path} must be a mapping")
        blocks.append(data)
    return blocks


@dataclass(frozen=True)
class Finding:
    status: str
    check: str
    detail: str

    def line(self) -> str:
        return f"{self.status}: {self.check}: {self.detail}"


@dataclass
class Artifact:
    id: str
    kind: str
    file: str
    metadata: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Repository:
    root: Path
    source: str
    artifacts: dict[str, Artifact] = field(default_factory=dict)
    # source artifact -> required artifact, with every edge backed by a declaration
    dependencies: dict[str, set[str]] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)

    def record(self, status: str, check: str, detail: str) -> None:
        self.findings.append(Finding(status, check, detail))

    @property
    def failures(self) -> list[Finding]:
        return [f for f in self.findings if f.status in ("FAIL", "BLOCKED")]

    def check_path(self, reference: str, check: str, base: Path | None = None) -> Path:
        path = contained_path(self.root, reference, base)
        if not path.is_file():
            raise StructureError(f"{check}: missing file: {reference}")
        self.record("PASS", check, path.relative_to(self.root).as_posix())
        return path

    def check_reference(self, reference: str, check: str, base: Path | None = None) -> None:
        try:
            self.check_path(reference, check, base)
        except StructureError as exc:
            self.record("FAIL", check, str(exc))

    def add(self, artifact: Artifact) -> None:
        if artifact.id in self.artifacts:
            raise StructureError(f"duplicate artifact id: {artifact.id}")
        if any(a.file == artifact.file for a in self.artifacts.values()):
            raise StructureError(f"duplicate artifact path: {artifact.file}")
        self.check_path(artifact.file, f"{artifact.kind}-file")
        self.artifacts[artifact.id] = artifact
        self.dependencies[artifact.id] = set()

    def resolve_dependency(self, value: str, kind: str) -> str | None:
        exact = self.artifacts.get(value)
        if exact and exact.kind == kind:
            return exact.id
        # Consolidated skills have repeated display names; only unique names resolve.
        candidates = [
            a.id
            for a in self.artifacts.values()
            if a.kind == kind and any(value in (m.get("id"), m.get("name")) for m in a.metadata)
        ]
        return candidates[0] if len(candidates) == 1 else None

    def declare(self, source: str, values: Any, kind: str, location: str) -> None:
        if not isinstance(values, list) or any(
            not isinstance(v, str) or not v.strip() for v in values
        ):
            self.record("FAIL", "dependency", f"{location}: expected a list of nonempty IDs")
            return
        for value in values:
            target = self.resolve_dependency(value, kind)
            if target is None:
                self.record("FAIL", "dependency", f"{location}: unknown/ambiguous {kind} {value!r}")
            else:
                self.dependencies[source].add(target)
                self.record("PASS", "dependency", f"{source} -> {target} ({location})")

    def as_manifest(self) -> dict[str, Any]:
        """Compatibility view, not an on-disk manifest or invented graph."""
        data: dict[str, Any] = {
            f"{kind}s": {
                "registry": [
                    {"id": a.id, "file": a.file} for a in self.artifacts.values() if a.kind == kind
                ]
            }
            for kind in KINDS
        }
        data["declaredDependencies"] = {
            source: sorted(targets) for source, targets in self.dependencies.items()
        }
        data["source"] = self.source
        data["root"] = str(self.root)
        return data


def _agents_links(repo: Repository) -> set[str]:
    path = repo.check_path("AGENTS.md", "agents")
    links: set[str] = set()
    for destination in re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
        destination = destination.strip().split()[0].strip("<>")
        url = urlsplit(destination)
        if url.scheme in ("https", "http", "mailto") or url.netloc or not url.path:
            continue
        if url.scheme:
            raise StructureError(f"unsupported local AGENTS link scheme: {destination}")
        resolved = repo.check_path(url.path, "agents-link")
        links.add(resolved.relative_to(repo.root).as_posix())
    if not links:
        raise StructureError("AGENTS.md has no local registry links")
    return links


def _legacy(repo: Repository, manifest_path: Path) -> None:
    doc = read_mapping(manifest_path)
    sections = [f"{kind}s" for kind in KINDS if f"{kind}s" in doc]
    if not sections:
        raise StructureError("unknown MANIFEST schema: typed artifact registries required")
    for section in sections:
        block = doc[section]
        if not isinstance(block, dict) or not isinstance(block.get("registry"), list):
            raise StructureError(f"malformed MANIFEST {section}.registry")
        for entry in block["registry"]:
            if (
                not isinstance(entry, dict)
                or not isinstance(entry.get("id"), str)
                or not entry["id"]
            ):
                raise StructureError(f"malformed MANIFEST {section} registry entry")
            path = repo.check_path(entry.get("file"), "manifest-file")
            repo.add(
                Artifact(
                    entry["id"],
                    section[:-1],
                    path.relative_to(repo.root).as_posix(),
                    metadata_blocks(path),
                )
            )
    if not repo.artifacts or not any(a.kind == "kernel" for a in repo.artifacts.values()):
        raise StructureError("empty MANIFEST registry or no kernels registered")
    graph = doc.get("dependencyGraph", {})
    if not isinstance(graph, dict):
        raise StructureError("malformed MANIFEST dependencyGraph")
    fields = {"skillsRequiringKernels": "skill", "playbookKernelRequirements": "playbook"}
    unknown = set(graph) - set(fields)
    if unknown:
        raise StructureError(f"unknown dependencyGraph fields: {sorted(unknown)}")
    for field_name, kind in fields.items():
        rows = graph.get(field_name, {})
        if not isinstance(rows, dict):
            raise StructureError(f"malformed dependencyGraph.{field_name}")
        for source, values in rows.items():
            if source not in repo.artifacts or repo.artifacts[source].kind != kind:
                repo.record(
                    "FAIL", "dependency", f"unknown {kind} source in {field_name}: {source}"
                )
                continue
            repo.declare(source, values, "kernel", f"dependencyGraph.{field_name}.{source}")


def _consolidated(repo: Repository, links: set[str]) -> None:
    from l9_ops_mcp.kernel_registry import KernelRegistry

    index = read_mapping(repo.check_path("AGENT_RETRIEVAL_INDEX.yaml", "retrieval-index"))
    files = index.get("files")
    if not isinstance(files, dict) or not files:
        raise StructureError("retrieval index requires a nonempty files mapping")
    for rel, meta in files.items():
        if not isinstance(meta, dict):
            raise StructureError(f"malformed retrieval index entry: {rel}")
        repo.check_path(rel, "indexed-file")
    registry = KernelRegistry.load(repo.root)
    kernels = registry.all()
    if not kernels:
        raise StructureError("empty canonical kernel registry")
    indexed = {k.canonical_path for k in kernels}
    actual = {
        p.relative_to(repo.root).as_posix()
        for p in (repo.root / "docs/kernels").rglob("*")
        if p.suffix in (".md", ".yaml", ".yml")
    }
    if actual != indexed:
        raise StructureError(
            f"canonical kernel index mismatch: unindexed={sorted(actual - indexed)}, "
            f"missing={sorted(indexed - actual)}"
        )
    for kernel in kernels:
        repo.add(
            Artifact(kernel.kernel_id, "kernel", kernel.canonical_path, [dict(kernel.raw_metadata)])
        )
        if kernel.canonical_path not in links:
            repo.record(
                "FAIL", "kernel-agents", f"not linked in AGENTS.md: {kernel.canonical_path}"
            )
        repo.record("PASS", "kernel-integrity", f"{kernel.kernel_id}: indexed SHA-256 verified")
        if not kernel.schema_valid:
            repo.record(
                "UNKNOWN",
                "kernel-content-schema",
                f"{kernel.kernel_id}: "
                + "; ".join(kernel.schema_errors)
                + " (not a structural/eval pass)",
            )
    patterns = {"skill": ("skills", "SKILL.md"), "playbook": ("playbooks", "PLAYBOOK.md")}
    for kind, (directory, pattern) in patterns.items():
        paths = set((repo.root / directory).rglob(pattern))
        if kind == "playbook":
            paths.update((repo.root / directory).rglob("playbook.yaml"))
        for path in sorted(paths):
            rel = path.relative_to(repo.root).as_posix()
            # Path identity avoids collisions in repeated optimize-kernel/review-code-l9 names.
            aid = path.parent.relative_to(repo.root / directory).as_posix()
            repo.add(Artifact(aid, kind, rel, metadata_blocks(path)))
    for path in sorted((repo.root / "prompts").rglob("*")):
        if path.is_file() and path.suffix in (".yaml", ".yml", ".md"):
            aid = path.relative_to(repo.root / "prompts").with_suffix("").as_posix()
            repo.add(
                Artifact(
                    aid, "prompt", path.relative_to(repo.root).as_posix(), metadata_blocks(path)
                )
            )
    if (repo.root / "ARTIFACT_MANIFEST.yaml").exists():
        doc = read_mapping(repo.root / "ARTIFACT_MANIFEST.yaml")
        rows = doc.get("artifacts")
        if not isinstance(rows, list) or not rows:
            raise StructureError("ARTIFACT_MANIFEST.yaml requires a nonempty artifacts list")
        for entry in rows:
            if not isinstance(entry, dict):
                raise StructureError("malformed ARTIFACT_MANIFEST entry")
            repo.check_path(entry.get("path"), "artifact-manifest-reference")


def _superseded_replacement(repo: Repository, artifact: Artifact, links: set[str]) -> str | None:
    statuses = {m["status"] for m in artifact.metadata if "status" in m}
    if "superseded" not in statuses:
        return None
    if artifact.kind != "playbook" or statuses != {"superseded"}:
        raise StructureError(f"invalid/conflicting superseded status: {artifact.file}")
    declarations = [m["superseded_by"] for m in artifact.metadata if "superseded_by" in m]
    if not declarations or any(not isinstance(v, str) or not v for v in declarations):
        raise StructureError(
            f"superseded playbook requires an explicit superseded_by path: {artifact.file}"
        )
    if len(set(declarations)) != 1:
        raise StructureError(f"conflicting superseded_by paths: {artifact.file}")
    path = repo.check_path(
        declarations[0], "superseded-replacement", (repo.root / artifact.file).parent
    )
    rel = path.relative_to(repo.root).as_posix()
    replacement = next((a for a in repo.artifacts.values() if a.file == rel), None)
    if replacement is None or replacement.kind != artifact.kind or replacement.id == artifact.id:
        raise StructureError(f"replacement must be a distinct registered playbook: {rel}")
    if rel not in links:
        raise StructureError(f"replacement must be linked by AGENTS.md: {rel}")
    if any(m.get("status", "active") != "active" for m in replacement.metadata):
        raise StructureError(f"replacement must be executable, not a supersession chain: {rel}")
    # The replacement is validated by the same global gate below. This never
    # waives a dependency/path failure on the replacement or other active files.
    return replacement.id


def _historical_references(repo: Repository, artifact: Artifact, replacement: str) -> None:
    repo.record(
        "NOT_APPLICABLE_WITH_REASON",
        "superseded-playbook-execution",
        f"{artifact.file}: explicitly superseded by registered {replacement}; "
        "original declarations retained below, not runtime dependencies",
    )
    for metadata in artifact.metadata:
        for field_name in (*KERNEL_DEP_FIELDS, *SKILL_DEP_FIELDS):
            if field_name not in metadata:
                continue
            values = metadata[field_name]
            if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values):
                raise StructureError(
                    f"malformed historical dependency declaration: {artifact.file}:{field_name}"
                )
            for value in values:
                repo.record(
                    "UNKNOWN",
                    "historical-dependency",
                    f"{artifact.file}:{field_name}: {value} (superseded, not readiness-proven)",
                )
        steps = metadata.get("steps", [])
        if not isinstance(steps, list) or any(not isinstance(s, dict) for s in steps):
            raise StructureError(f"malformed historical steps: {artifact.file}")
        for step in steps:
            if "file" in step:
                path = contained_path(repo.root, step["file"], (repo.root / artifact.file).parent)
                repo.record(
                    "UNKNOWN",
                    "historical-step",
                    f"{artifact.file}: {step['file']} "
                    f"({'present' if path.is_file() else 'unavailable'}; superseded, not executed)",
                )


def _declared_references(repo: Repository, links: set[str]) -> None:
    for artifact in repo.artifacts.values():
        replacement = _superseded_replacement(repo, artifact, links)
        if replacement:
            _historical_references(repo, artifact, replacement)
            continue
        base = (repo.root / artifact.file).parent
        for metadata in artifact.metadata:
            for field_name in KERNEL_DEP_FIELDS:
                if field_name in metadata:
                    repo.declare(
                        artifact.id, metadata[field_name], "kernel", f"{artifact.file}:{field_name}"
                    )
            for field_name in SKILL_DEP_FIELDS:
                if field_name in metadata:
                    repo.declare(
                        artifact.id, metadata[field_name], "skill", f"{artifact.file}:{field_name}"
                    )
            steps = metadata.get("steps")
            if steps is not None:
                if not isinstance(steps, list) or any(not isinstance(s, dict) for s in steps):
                    raise StructureError(f"malformed steps in {artifact.file}")
                for step in steps:
                    if "file" in step:
                        repo.check_reference(step["file"], "declared-step", base)
        if artifact.kind == "playbook":
            text = (repo.root / artifact.file).read_text(encoding="utf-8")
            for rel in set(
                re.findall(
                    r"(?<![A-Za-z0-9_/])((?:steps|handoffs|data-types)/[A-Za-z0-9_./-]+\.(?:md|yaml|yml|json))",
                    text,
                )
            ):
                repo.check_reference(rel, "playbook-reference", base)
    edge_count = sum(len(v) for v in repo.dependencies.values())
    repo.record("PASS", "declared-dependency-inventory", f"{edge_count} resolved declared edges")
    repo.record(
        "NOT_APPLICABLE_WITH_REASON",
        "content-evals",
        "structural wiring does not execute promptfoo, assert authored completeness, "
        "or certify runtime kernel schema applicability",
    )


def load_repository(root: Path = ROOT, manifest: str | None = None) -> Repository:
    root = root.resolve()
    repo = Repository(
        root,
        "legacy MANIFEST"
        if manifest or (root / "MANIFEST.json").exists()
        else "canonical registry + AGENTS + filesystem declarations",
    )
    links = _agents_links(repo)
    if manifest or (root / "MANIFEST.json").exists():
        _legacy(repo, contained_path(root, manifest or "MANIFEST.json"))
    else:
        _consolidated(repo, links)
    _declared_references(repo, links)
    return repo
