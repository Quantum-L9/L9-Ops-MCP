# --- L9_META ---
# l9_schema: 1
# component: inject_dora_complete
# artifact_type: context
# tags: [general]
# retrieval: on_demand
# status: active
# --- /L9_META ---


#!/usr/bin/env python3
"""
DORA Block Report (read-only)
=============================
Reports which files lack the three blocks required by dora-contract.yaml:
  1. Header Meta (``__dora_meta__``)
  2. Footer Meta (``__dora_footer__``)
  3. DORA trace block (``__l9_trace__``; Python only)

The former ``--execute``/``--force`` injection modes were removed (decision
D-18 A): they inserted blocks before ``from __future__`` imports and leading
comments, wrote unescaped values into string literals, and reported success
after corrupting files. This script never writes a scanned file.

Usage:
    python scripts/inject_dora_complete.py --repo . --dry-run --report report.json
    python scripts/inject_dora_complete.py --repo . --file path/to/file.py

Exit codes: 0 every file checked; 1 any file unreadable/unparseable, no files
found, or report not writable; 2 usage error.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Inject Dora Complete",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-18T02:10:54Z",
    "updated_at": "2026-01-25T14:59:57Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "inject_dora_complete",
    "type": "router",
    "status": "deprecated",
    "integrates_with": {
        "api_endpoints": ["GET /path", "POST /path"],
        "datasources": [
            "Anthropic API",
            "Gmail API",
            "HTTP API",
            "Neo4j",
            "OpenAI API",
            "Perplexity API",
            "PostgreSQL",
            "Redis",
            "S3",
            "Slack API",
        ],
        "memory_layers": ["working_memory", "episodic_memory", "semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
import ast
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ============================================================================
# SCOPE
#
# Directory names excluded from the scan. Matched against the path components
# *relative to --repo*, never as substrings: ".git" must not exclude ".github",
# and a --repo path that merely contains "tests" must not exclude everything.
SKIP_DIRS = frozenset(
    {
        "_archived",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        ".git",
        "tests",
        "deploy",
        ".cursor-commands",
        ".backup",
        "current_work",
        "codegen",
    }
)

PY_SUFFIXES = (".py",)
YAML_SUFFIXES = (".yaml", ".yml")

# Layer mapping based on directory structure (used for component ids).
LAYER_MAP = {
    "core": "foundation",
    "agents": "intelligence",
    "api": "operations",
    "memory": "learning",
    "runtime": "operations",
    "services": "operations",
    "orchestration": "intelligence",
    "orchestrators": "intelligence",
    "world_model": "learning",
    "simulation": "learning",
    "governance": "security",
    "compliance": "security",
    "security": "security",
    "config": "foundation",
    "schemas": "foundation",
    "scripts": "operations",
    "tests": "operations",
    "email_agent": "integration",
    "mac_agent": "integration",
    "slack_agent": "integration",
    "mcp_memory": "integration",
    "clients": "integration",
    "workers": "operations",
    "telemetry": "operations",
    "ir_engine": "intelligence",
    "graph_adapter": "integration",
    "collaborative_cells": "intelligence",
    "dev": "operations",
    "codegen": "foundation",
}


class FileCheckError(Exception):
    """A scanned file could not be read or parsed; it is reported as failed."""


@dataclass
class FileStatus:
    """Which DORA blocks a single file is missing (read-only observation)."""

    missing_header: bool = False
    missing_footer: bool = False
    missing_trace: bool = False
    legacy: bool = False
    classes: list[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return not (self.missing_header or self.missing_footer or self.missing_trace)


# ============================================================================
# REPORT ENGINE


class DoraCompleteInjector:
    """Read-only DORA block report.

    The former injection modes (``--execute``/``--force``) were removed under
    decision D-18 A because they corrupted files. This class only reads.
    """

    def __init__(self, repo_path: str) -> None:
        self.repo_path = Path(repo_path).resolve()
        self.files_to_process: list[Path] = []
        self.component_id_counter: dict[str, int] = {}

    # -- discovery -----------------------------------------------------------

    def _is_skipped(self, path: Path) -> bool:
        rel_dirs = path.relative_to(self.repo_path).parts[:-1]
        return any(part in SKIP_DIRS for part in rel_dirs)

    def scan_repository(self, single_file: str | None = None) -> None:
        """Collect Python and YAML files to report on (sorted, deterministic)."""
        if single_file:
            file_path = Path(single_file)
            if not file_path.is_absolute():
                file_path = self.repo_path / file_path
            file_path = file_path.resolve()
            if file_path.is_file() and file_path.suffix in PY_SUFFIXES + YAML_SUFFIXES:
                self.files_to_process = [file_path]
            return

        found: list[Path] = []
        for suffix in PY_SUFFIXES + YAML_SUFFIXES:
            for path in self.repo_path.rglob(f"*{suffix}"):
                if path.is_file() and not self._is_skipped(path):
                    found.append(path)
        self.files_to_process = sorted(set(found))

    # -- per-file observation ----------------------------------------------

    @staticmethod
    def _read_text(file_path: Path) -> str:
        try:
            # utf-8-sig: a UTF-8 BOM is valid at the start of Python source.
            return file_path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            msg = f"unreadable: {exc}"
            raise FileCheckError(msg) from exc

    def check_file(self, file_path: Path) -> FileStatus:
        """Observe which DORA blocks ``file_path`` lacks. Never writes."""
        content = self._read_text(file_path)

        if file_path.suffix in YAML_SUFFIXES:
            return FileStatus(
                missing_header=not ("# DORA META" in content or "# component_name:" in content),
                missing_footer=not ("# DORA FOOTER" in content or "# tags:" in content),
                missing_trace=False,  # YAML files carry no runtime trace block
            )

        try:
            tree = ast.parse(content, filename=str(file_path))
        except (SyntaxError, ValueError) as exc:
            msg = f"unparseable: {exc}"
            raise FileCheckError(msg) from exc

        # Only real module-level assignments count, never strings or comments.
        assigned: set[str] = set()
        for node in tree.body:
            targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
            elif isinstance(node, ast.AnnAssign):
                targets = [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    assigned.add(target.id)

        return FileStatus(
            missing_header="__dora_meta__" not in assigned,
            missing_footer="__dora_footer__" not in assigned,
            missing_trace="__l9_trace__" not in assigned,
            legacy="__dora_block__" in assigned,
            classes=[node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)],
        )

    def _infer_layer(self, file_path: Path) -> str:
        for part in file_path.relative_to(self.repo_path).parts:
            if part in LAYER_MAP:
                return LAYER_MAP[part]
        return "operations"

    def _generate_component_id(self, file_path: Path, layer: str) -> str:
        """Generate a component id per contract format (prefix + counter)."""
        parts = file_path.relative_to(self.repo_path).parts
        domain_abbrev = parts[0][:3].upper() if len(parts) >= 2 else "L9"
        prefix = f"{domain_abbrev}-{layer[:4].upper()}"
        self.component_id_counter[prefix] = self.component_id_counter.get(prefix, 0) + 1
        return f"{prefix}-{self.component_id_counter[prefix]:03d}"

    # -- aggregation ---------------------------------------------------------

    def process_all_files(self) -> dict[str, Any]:
        """Build the report. Counts are "would inject" counts per block.

        ``header_injected``/``footer_injected``/``trace_injected`` keep their
        historical names (CI reads ``header_injected``) and mean: files that lack
        the block. ``skipped`` counts files that already carry every applicable
        block; ``failed`` counts files that could not be read or parsed.
        """
        results: dict[str, Any] = {
            "mode": "report",
            "total_files": len(self.files_to_process),
            "header_injected": 0,
            "footer_injected": 0,
            "trace_injected": 0,
            "skipped": 0,
            "failed": 0,
            "legacy_migration_needed": 0,
            "files": [],
            "failures": [],
        }

        for file_path in self.files_to_process:
            try:
                status = self.check_file(file_path)
            except FileCheckError as exc:
                results["failed"] += 1
                results["failures"].append({"file": str(file_path), "error": str(exc)})
                continue

            component_id = self._generate_component_id(file_path, self._infer_layer(file_path))
            if status.legacy:
                results["legacy_migration_needed"] += 1
            elif status.complete:
                results["skipped"] += 1
            else:
                results["header_injected"] += int(status.missing_header)
                results["footer_injected"] += int(status.missing_footer)
                results["trace_injected"] += int(status.missing_trace)

            results["files"].append(
                {
                    "file": str(file_path),
                    "component_id": component_id,
                    "missing": {
                        "header": status.missing_header,
                        "footer": status.missing_footer,
                        "trace": status.missing_trace,
                    },
                    "legacy": status.legacy,
                    "classes": status.classes,
                }
            )

        return results

    @staticmethod
    def generate_report(results: dict[str, Any], output_path: str) -> None:
        """Write the JSON report and print a summary."""
        Path(output_path).write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

        print("DORA block report (read-only)")
        print(f"total files: {results['total_files']}")
        print(f"missing header meta: {results['header_injected']}")
        print(f"missing footer meta: {results['footer_injected']}")
        print(f"missing trace block: {results['trace_injected']}")
        print(f"complete (all blocks present): {results['skipped']}")
        print(f"legacy migration needed: {results['legacy_migration_needed']}")
        print(f"failed: {results['failed']}")
        for failure in results["failures"]:
            print(f"  FAILED {failure['file']}: {failure['error']}", file=sys.stderr)
        print(f"report: {output_path}")


# ============================================================================
# MAIN


def main(argv: list[str] | None = None) -> int:
    """Run the read-only DORA report.

    Exit codes: 0 report written and every file checked; 1 any file failed,
    no files found, or the report could not be written; 2 usage error
    (including the removed ``--execute``/``--force`` modes).
    """
    parser = argparse.ArgumentParser(
        description=(
            "Report which files lack contract DORA blocks (read-only). "
            "The --execute/--force injection modes were removed (D-18 A)."
        )
    )
    parser.add_argument("--repo", required=True, help="Path to the repository to scan")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Accepted for compatibility; the report is always read-only",
    )
    parser.add_argument("--file", help="Report on a single file only")
    parser.add_argument(
        "--report",
        default="dora_complete_injection_report.json",
        help="Output report path",
    )
    args = parser.parse_args(argv)

    report_path = Path(args.report).resolve()
    if not report_path.is_relative_to(Path.cwd().resolve()):
        print(
            f"error: --report must stay inside the working directory: {args.report}",
            file=sys.stderr,
        )
        return 1

    injector = DoraCompleteInjector(args.repo)
    if not injector.repo_path.is_dir():
        print(f"error: --repo is not a directory: {args.repo}", file=sys.stderr)
        return 1

    injector.scan_repository(single_file=args.file)
    if not injector.files_to_process:
        print("error: no files found to report on", file=sys.stderr)
        return 1

    results = injector.process_all_files()
    try:
        injector.generate_report(results, str(report_path))
    except OSError as exc:
        print(f"error: cannot write report {args.report}: {exc}", file=sys.stderr)
        return 1

    return 1 if results["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "api-gateway",
        "ast",
        "async",
        "auth",
        "authorization",
        "batch-processing",
        "caching",
        "cli",
        "code-quality",
    ],
    "keywords": [
        "all",
        "block",
        "blocks",
        "complete",
        "dora",
        "files",
        "footer",
        "generate",
    ],
    "business_value": "Provides inject dora complete components including ClassInfo, HeaderMeta, FooterMeta",
    "last_modified": "2026-01-25T14:59:57Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
