"""Faithful reproduction of a frozen search run from its raw payloads.

Unlike a copy of the already-processed CSV, this rebuilds every record by
re-parsing the raw arXiv XML and Crossref ``.json.gz`` files saved under a run
directory, then re-runs the exact same processing pipeline
(:func:`quantum_diffusion_search.cli.process_and_export`) used by ``search``.
The reproduced tables are written under ``data/reproduced/`` and compared,
column by column, against the committed outputs so that any drift is reported
explicitly.

Because the raw payloads are the authoritative acquisition record, a successful
reproduction demonstrates that the processed artifacts can be regenerated from
them deterministically, without contacting any external API.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

import feedparser
import pandas as pd
import yaml

from .clients.arxiv_client import parse_arxiv_entry
from .clients.crossref_client import parse_crossref_item

# Columns that legitimately vary between runs and must be ignored when diffing.
_VOLATILE_COLUMNS = {"retrieved_at_utc"}


def _load_config(raw_run: Path) -> dict[str, Any]:
    cfg_path = raw_run / "resolved_search_config.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(cfg_path)
    with cfg_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _parse_arxiv(raw_run: Path, cfg: dict[str, Any], run_id: str) -> list[dict[str, Any]]:
    arxiv_dir = raw_run / "arxiv"
    records: list[dict[str, Any]] = []
    if not arxiv_dir.exists():
        return records
    for query in cfg["queries"]:
        qid = query["query_id"]
        pages = sorted(
            arxiv_dir.glob(f"{qid}_start*.xml"),
            key=lambda p: int(p.stem.split("start")[-1]),
        )
        for raw_file in pages:
            feed = feedparser.parse(raw_file.read_bytes())
            for entry in getattr(feed, "entries", []):
                records.append(
                    parse_arxiv_entry(
                        entry,
                        query_id=qid,
                        query_text=query["arxiv_query"],
                        run_id=run_id,
                        raw_source_file=str(raw_file),
                    )
                )
    return records


def _parse_crossref(raw_run: Path, source: str, cfg: dict[str, Any], run_id: str) -> list[dict[str, Any]]:
    pub_cfg = cfg["publishers"][source]
    source_dir = raw_run / f"{source}_crossref"
    records: list[dict[str, Any]] = []
    if not source_dir.exists():
        return records
    for prefix in pub_cfg["doi_prefixes"]:
        prefix_tag = prefix.replace(".", "_")
        for query in cfg["queries"]:
            qid = query["query_id"]
            pages = sorted(
                source_dir.glob(f"{qid}_{prefix_tag}_page*.json.gz"),
                key=lambda p: int(p.name.split("page")[-1].split(".")[0]),
            )
            for raw_file in pages:
                with gzip.open(raw_file, "rt", encoding="utf-8") as handle:
                    data = json.load(handle)
                items = data.get("message", {}).get("items") or []
                for item in items:
                    parsed = parse_crossref_item(
                        item,
                        query_id=qid,
                        query_text=query["crossref_query"],
                        run_id=run_id,
                        database_scope=pub_cfg["database_scope"],
                        retrieval_method=pub_cfg["retrieval_method"],
                        doi_prefix=prefix,
                        raw_source_file=str(raw_file),
                    )
                    if (parsed.get("doi_normalized") or "").startswith(prefix.lower() + "/"):
                        records.append(parsed)
    return records


def rebuild_records(raw_run: Path, cfg: dict[str, Any], run_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Re-parse raw payloads in the same source/query order used by ``search``."""
    records: list[dict[str, Any]] = []
    arxiv_records: list[dict[str, Any]] = []
    for source in cfg.get("sources", []):
        if source == "arxiv":
            rows = _parse_arxiv(raw_run, cfg, run_id)
            arxiv_records.extend(rows)
            records.extend(rows)
        elif source in {"ieee", "springer"}:
            records.extend(_parse_crossref(raw_run, source, cfg, run_id))
        else:
            raise ValueError(f"Unknown source: {source}")
    return records, arxiv_records


def _compare(reproduced_dir: Path, committed_dir: Path) -> tuple[bool, list[str]]:
    messages: list[str] = []
    ok = True
    for name in ["all_source_records.csv", "deduplicated_records.csv", "relevant_candidates.csv"]:
        rep_path = reproduced_dir / name
        com_path = committed_dir / name
        if not com_path.exists():
            messages.append(f"[skip] no committed {name} to compare against")
            continue
        if not rep_path.exists():
            ok = False
            messages.append(f"[FAIL] reproduced {name} was not produced")
            continue
        rep = pd.read_csv(rep_path, dtype=str, keep_default_na=False)
        com = pd.read_csv(com_path, dtype=str, keep_default_na=False)
        if len(rep) != len(com):
            ok = False
            messages.append(f"[FAIL] {name}: row count {len(rep)} (reproduced) != {len(com)} (committed)")
            continue
        shared = [c for c in com.columns if c in rep.columns and c not in _VOLATILE_COLUMNS]
        key = "record_id" if "record_id" in shared else shared[0]
        rep_s = rep.sort_values(key).reset_index(drop=True)[shared]
        com_s = com.sort_values(key).reset_index(drop=True)[shared]
        if rep_s.equals(com_s):
            messages.append(f"[ok] {name}: {len(rep)} rows reproduced identically ({len(shared)} columns compared)")
        else:
            diff_cols = [c for c in shared if not rep_s[c].equals(com_s[c])]
            ok = False
            messages.append(f"[FAIL] {name}: {len(rep)} rows but differing columns: {diff_cols[:8]}")
    return ok, messages


def reproduce_run(raw_run: Path, *, out_dir: Path = Path("data/reproduced"), committed_dir: Path = Path("data/processed")) -> int:
    from .cli import process_and_export  # local import to avoid an import cycle

    cfg = _load_config(raw_run)
    run_id = raw_run.name
    records, arxiv_records = rebuild_records(raw_run, cfg, run_id)
    if not records:
        raise RuntimeError(f"No records could be rebuilt from raw payloads under {raw_run}")

    processed_dir = out_dir / "processed"
    reports_dir = out_dir / "reports"
    processed_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    process_and_export(records, cfg, run_id, processed_dir, reports_dir, [], arxiv_records=arxiv_records)

    ok, messages = _compare(processed_dir, committed_dir)
    for line in messages:
        print(line)
    print(f"\nReproduction {'MATCHES' if ok else 'DIFFERS FROM'} the committed outputs.")
    print(f"Reproduced tables written to: {processed_dir}")
    return 0 if ok else 1
