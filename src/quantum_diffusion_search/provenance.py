"""Run manifests and checksums."""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import sha256_file, sha256_text, stable_json


def git_info() -> dict[str, Any]:
    def run(args: list[str]) -> str | None:
        try:
            return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()
        except Exception:
            return None

    return {
        "commit": run(["git", "rev-parse", "HEAD"]),
        "status": run(["git", "status", "--short"]),
    }


def dependency_versions() -> dict[str, str]:
    pkgs = ["requests", "feedparser", "pandas", "pyarrow", "openpyxl", "yaml", "rapidfuzz", "matplotlib"]
    versions = {}
    for name in pkgs:
        try:
            mod = __import__("yaml" if name == "yaml" else name)
            versions[name] = getattr(mod, "__version__", "unknown")
        except Exception:
            versions[name] = "not installed"
    return versions


def build_manifest(
    *,
    run_id: str,
    command: str,
    resolved_config: dict[str, Any],
    started_at_utc: str,
    finished_at_utc: str | None,
    logs: list[dict[str, Any]],
    produced_files: list[str],
    failures: list[str] | None = None,
) -> dict[str, Any]:
    checksums = {p: sha256_file(p) for p in produced_files if Path(p).exists()}
    return {
        "run_id": run_id,
        "started_at_utc": started_at_utc,
        "finished_at_utc": finished_at_utc or datetime.now(UTC).isoformat(),
        "command": command,
        "configuration_sha256": sha256_text(stable_json(resolved_config)),
        "resolved_config": resolved_config,
        "python": sys.version,
        "platform": platform.platform(),
        "dependencies": dependency_versions(),
        "git": git_info(),
        "sources_consulted": sorted({x.get("database_scope") for x in logs if x.get("database_scope")}),
        "queries_executed": logs,
        "http_requests": sum(int(x.get("http_requests") or 0) for x in logs),
        "results_reported_by_api": sum(int(x.get("api_total_results") or 0) for x in logs),
        "results_retrieved": sum(int(x.get("retrieved_records") or 0) for x in logs),
        "failures": failures or [],
        "truncations": [x for x in logs if x.get("truncated")],
        "produced_files": produced_files,
        "sha256": checksums,
    }


def write_manifest(manifest: dict[str, Any], path: str | Path) -> None:
    Path(path).write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
