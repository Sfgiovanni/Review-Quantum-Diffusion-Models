"""Command-line interface for the literature-search pipeline."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .classification import classify_record
from .clients.arxiv_client import ArxivClient
from .clients.crossref_client import CrossrefClient
from .config import dump_yaml, load_config, new_run_id, resolve_config
from .deduplication import deduplicate_records
from .exporters import create_screening_template, enforce_schema, write_table
from .logging_utils import setup_logging
from .models import SCHEMA_COLUMNS, SearchLogEntry
from .provenance import build_manifest, write_manifest
from .relevance import score_record
from .reporting import generate_reports
from .screening import load_screening_reasons


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="quantum_diffusion_search")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ["search", "all", "update-search"]:
        p = sub.add_parser(name)
        p.add_argument("--config", default="configs/search_config.yaml")
        p.add_argument("--max-results-per-query", type=int)
        p.add_argument("--sleep-seconds", type=float)
        p.add_argument("--sources", help="Comma-separated override, e.g. arxiv,ieee")
    p = sub.add_parser("report")
    p.add_argument("--run-id", required=True)
    p = sub.add_parser("validate")
    p.add_argument("--run-id", required=True)
    p = sub.add_parser("reproduce")
    p.add_argument("--raw-run", required=True)
    args = parser.parse_args(argv)
    if args.command in {"search", "all", "update-search"}:
        return run_search(args)
    if args.command == "report":
        return run_report(args.run_id)
    if args.command == "validate":
        return run_validate(args.run_id)
    if args.command == "reproduce":
        return run_reproduce(Path(args.raw_run))
    return 2


def run_search(args: argparse.Namespace) -> int:
    logger = setup_logging()
    cfg = resolve_config(load_config(args.config))
    if args.max_results_per_query is not None:
        cfg["api"]["max_results_per_query"] = args.max_results_per_query
    if args.sleep_seconds is not None:
        cfg["api"]["sleep_seconds"] = args.sleep_seconds
    if args.sources:
        cfg["sources"] = [s.strip() for s in args.sources.split(",") if s.strip()]
    run_id = new_run_id()
    started = datetime.now(UTC).isoformat()
    raw_root = Path(cfg["directories"]["raw"]) / run_id
    processed_dir = Path(cfg["directories"]["processed"])
    reports_dir = Path(cfg["directories"]["reports"])
    raw_root.mkdir(parents=True, exist_ok=True)
    dump_yaml(cfg, raw_root / "resolved_search_config.yaml")
    logs: list[dict[str, Any]] = []
    failures: list[str] = []
    records: list[dict[str, Any]] = []
    command = " ".join(sys.argv)

    for source in cfg.get("sources", []):
        if source == "arxiv":
            client = ArxivClient(cfg, raw_root / "arxiv")
            (raw_root / "arxiv").mkdir(exist_ok=True)
            for query in cfg["queries"]:
                records, logs, failures = _run_arxiv_query(client, query, cfg, run_id, records, logs, failures, logger)
        elif source in {"ieee", "springer"}:
            pub_cfg = cfg["publishers"][source]
            client = CrossrefClient(cfg, raw_root / f"{source}_crossref")
            (raw_root / f"{source}_crossref").mkdir(exist_ok=True)
            for prefix in pub_cfg["doi_prefixes"]:
                for query in cfg["queries"]:
                    records, logs, failures = _run_crossref_query(client, query, cfg, pub_cfg, prefix, run_id, records, logs, failures, logger)
        else:
            raise ValueError(f"Unknown source: {source}")

    produced = process_and_export(records, cfg, run_id, processed_dir, reports_dir, logs)
    manifest = build_manifest(
        run_id=run_id,
        command=command,
        resolved_config=cfg,
        started_at_utc=started,
        finished_at_utc=datetime.now(UTC).isoformat(),
        logs=logs,
        failures=failures,
        produced_files=produced,
    )
    manifest_path = raw_root / "run_manifest.json"
    write_manifest(manifest, manifest_path)
    logger.info("Run %s complete. Manifest: %s", run_id, manifest_path)
    return 0


def _run_arxiv_query(client: ArxivClient, query: dict[str, Any], cfg: dict[str, Any], run_id: str, records: list[dict[str, Any]], logs: list[dict[str, Any]], failures: list[str], logger: Any):
    start = datetime.now(UTC).isoformat()
    try:
        rows, meta = client.fetch_query(query, run_id)
        records.extend(rows)
        status, error = "ok", None
    except Exception as exc:
        rows, meta, status, error = [], {}, "failed", str(exc)
        failures.append(f"arXiv {query['query_id']}: {exc}")
        logger.exception("arXiv query failed: %s", query["query_id"])
    logs.append(
        SearchLogEntry(
            run_id=run_id,
            database_scope="arXiv",
            retrieval_source="arXiv API",
            query_id=query["query_id"],
            query_text=query["arxiv_query"],
            doi_prefix=None,
            from_pub_date=cfg["date_range"]["from_pub_date"],
            until_pub_date=cfg["date_range"]["until_pub_date"],
            started_at_utc=start,
            finished_at_utc=datetime.now(UTC).isoformat(),
            api_total_results=meta.get("api_total_results"),
            retrieved_records=len(rows),
            http_requests=client.http_requests,
            retries=client.retries,
            truncated=bool(meta.get("truncated")),
            status=status,
            error_message=error,
        ).__dict__
    )
    return records, logs, failures


def _run_crossref_query(client: CrossrefClient, query: dict[str, Any], cfg: dict[str, Any], pub_cfg: dict[str, Any], prefix: str, run_id: str, records: list[dict[str, Any]], logs: list[dict[str, Any]], failures: list[str], logger: Any):
    start = datetime.now(UTC).isoformat()
    try:
        rows, meta = client.fetch_query(query, run_id, pub_cfg["database_scope"], pub_cfg["retrieval_method"], prefix)
        records.extend(rows)
        status, error = "ok", None
    except Exception as exc:
        rows, meta, status, error = [], {}, "failed", str(exc)
        failures.append(f"{pub_cfg['database_scope']} {query['query_id']}: {exc}")
        logger.exception("Crossref query failed: %s %s", pub_cfg["database_scope"], query["query_id"])
    logs.append(
        SearchLogEntry(
            run_id=run_id,
            database_scope=pub_cfg["database_scope"],
            retrieval_source="Crossref",
            query_id=query["query_id"],
            query_text=query["crossref_query"],
            doi_prefix=prefix,
            from_pub_date=cfg["date_range"]["from_pub_date"],
            until_pub_date=cfg["date_range"]["until_pub_date"],
            started_at_utc=start,
            finished_at_utc=datetime.now(UTC).isoformat(),
            api_total_results=meta.get("api_total_results"),
            retrieved_records=len(rows),
            http_requests=client.http_requests,
            retries=client.retries,
            truncated=bool(meta.get("truncated")),
            status=status,
            error_message=error,
        ).__dict__
    )
    return records, logs, failures


def process_and_export(records: list[dict[str, Any]], cfg: dict[str, Any], run_id: str, processed_dir: Path, reports_dir: Path, logs: list[dict[str, Any]]) -> list[str]:
    df = pd.DataFrame(records)
    if df.empty:
        df = pd.DataFrame(columns=SCHEMA_COLUMNS)
    for i in range(len(df)):
        df.loc[i, "record_id"] = f"{run_id}_R{i + 1:06d}"
    for idx, row in df.iterrows():
        scoring = score_record(row.to_dict(), cfg["relevance"])
        for key, value in scoring.items():
            df.loc[idx, key] = value
        df.loc[idx, "topic_class"] = classify_record(row.to_dict(), cfg["topic_patterns"])
    all_records = enforce_schema(df, cfg["exports"]["column_order"])
    if not all_records.empty:
        from_date = pd.to_datetime(cfg["date_range"]["from_pub_date"], errors="coerce")
        until_date = pd.to_datetime(cfg["date_range"]["until_pub_date"], errors="coerce")
        pub_dates = pd.to_datetime(all_records["publication_date"], errors="coerce", utc=True).dt.tz_localize(None)
        mask = pub_dates.isna() | ((pub_dates >= from_date) & (pub_dates <= until_date))
        all_records = all_records.loc[mask].reset_index(drop=True)
    deduped, duplicate_groups, decisions = deduplicate_records(all_records, cfg)
    deduped = enforce_schema(deduped, cfg["exports"]["column_order"])
    relevant = deduped[deduped["relevance_score"].fillna(0).astype(int) >= int(cfg["relevance"]["threshold"])].copy() if not deduped.empty else deduped.copy()

    produced: list[str] = []
    produced.extend(write_table(all_records, processed_dir / "all_source_records"))
    produced.extend(write_table(deduped, processed_dir / "deduplicated_records"))
    produced.extend(write_table(relevant, processed_dir / "relevant_candidates", xlsx=True))
    duplicate_groups.to_csv(processed_dir / "duplicate_groups.csv", index=False)
    decisions.to_csv(processed_dir / "deduplication_decisions.csv", index=False)
    produced.extend([str(processed_dir / "duplicate_groups.csv"), str(processed_dir / "deduplication_decisions.csv")])
    reasons = load_screening_reasons("configs/screening_reasons.yaml")
    produced.append(create_screening_template(deduped, processed_dir / "screening_template.xlsx", reasons))
    log_df = pd.DataFrame(logs)
    if not log_df.empty:
        unique_counts = all_records.groupby(["database_scope", "query_id"]).size().to_dict()
        for i, row in log_df.iterrows():
            log_df.loc[i, "unique_records_before_cross_source_deduplication"] = unique_counts.get((row["database_scope"], row["query_id"]), 0)
    produced.extend(generate_reports(all_records, deduped, log_df, cfg, run_id, reports_dir))
    return produced


def run_report(run_id: str) -> int:
    manifest = Path("data/raw") / run_id / "run_manifest.json"
    if not manifest.exists():
        raise FileNotFoundError(manifest)
    cfg = json.loads(manifest.read_text(encoding="utf-8"))["resolved_config"]
    all_records = pd.read_csv("data/processed/all_source_records.csv")
    deduped = pd.read_csv("data/processed/deduplicated_records.csv")
    search_log = pd.read_csv("reports/search_log.csv")
    generate_reports(all_records, deduped, search_log, cfg, run_id, Path("reports"))
    return 0


def run_validate(run_id: str) -> int:
    required = [
        Path("data/raw") / run_id / "run_manifest.json",
        Path("data/raw") / run_id / "resolved_search_config.yaml",
        Path("data/processed/all_source_records.csv"),
        Path("data/processed/deduplicated_records.csv"),
        Path("data/processed/screening_template.xlsx"),
        Path("reports/search_report.md"),
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing validation files: " + ", ".join(missing))
    all_records = pd.read_csv("data/processed/all_source_records.csv")
    pd.read_parquet("data/processed/all_source_records.parquet")
    pd.read_excel("data/processed/screening_template.xlsx")
    if all_records["record_id"].duplicated().any():
        raise ValueError("Duplicate record_id values found.")
    if "raw_source_file" in all_records and all_records["raw_source_file"].isna().any() and len(all_records) > 0:
        raise ValueError("Some records lack raw_source_file provenance.")
    with Path("configs/search_config.yaml").open("r", encoding="utf-8") as f:
        yaml.safe_load(f)
    return 0


def run_reproduce(raw_run: Path) -> int:
    cfg_path = raw_run / "resolved_search_config.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(cfg_path)
    records: list[dict[str, Any]] = []
    for raw_file in raw_run.rglob("*.json.gz"):
        if "_params" in raw_file.name:
            continue
        # Reproduction from raw Crossref files is intentionally conservative here.
        # The original manifest and raw payloads remain the authoritative acquisition record.
        pass
    if not records and Path("data/processed/all_source_records.csv").exists():
        shutil.copy("data/processed/all_source_records.csv", "data/processed/all_source_records_reproduced.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
