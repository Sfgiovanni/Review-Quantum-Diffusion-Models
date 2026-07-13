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
from .final_screening import build_final_screening
from .legacy import reconcile_legacy, reproduce_legacy_from_arxiv_records
from .logging_utils import setup_logging
from .models import SCHEMA_COLUMNS, SearchLogEntry
from .provenance import build_manifest, write_manifest
from .quality import query_quality_indicators
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
    p = sub.add_parser("apply-screening")
    p.add_argument("--screening", default="data/screening/manual_screening.csv")
    p.add_argument("--processed", default="data/processed")
    p.add_argument("--reports", default="reports")
    p.add_argument("--corpus-from", type=int, default=2025)
    p.add_argument("--corpus-to", type=int, default=2026)
    args = parser.parse_args(argv)
    if args.command in {"search", "all", "update-search"}:
        return run_search(args)
    if args.command == "report":
        return run_report(args.run_id)
    if args.command == "validate":
        return run_validate(args.run_id)
    if args.command == "reproduce":
        return run_reproduce(Path(args.raw_run))
    if args.command == "apply-screening":
        from .apply_screening import apply_screening
        summary = apply_screening(Path(args.screening), Path(args.processed), Path(args.reports), corpus_from=args.corpus_from, corpus_to=args.corpus_to)
        for key, value in summary.items():
            print(f"{key}: {value}")
        return 0
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
    arxiv_records: list[dict[str, Any]] = []
    command = " ".join(sys.argv)

    for source in cfg.get("sources", []):
        if source == "arxiv":
            client = ArxivClient(cfg, raw_root / "arxiv")
            (raw_root / "arxiv").mkdir(exist_ok=True)
            for query in cfg["queries"]:
                before = len(records)
                records, logs, failures = _run_arxiv_query(client, query, cfg, run_id, records, logs, failures, logger)
                arxiv_records.extend(records[before:])
        elif source in {"ieee", "springer"}:
            pub_cfg = cfg["publishers"][source]
            client = CrossrefClient(cfg, raw_root / f"{source}_crossref")
            (raw_root / f"{source}_crossref").mkdir(exist_ok=True)
            for prefix in pub_cfg["doi_prefixes"]:
                for query in cfg["queries"]:
                    records, logs, failures = _run_crossref_query(client, query, cfg, pub_cfg, prefix, run_id, records, logs, failures, logger)
        else:
            raise ValueError(f"Unknown source: {source}")

    produced = process_and_export(records, cfg, run_id, processed_dir, reports_dir, logs, arxiv_records=arxiv_records)
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


def process_and_export(
    records: list[dict[str, Any]],
    cfg: dict[str, Any],
    run_id: str,
    processed_dir: Path,
    reports_dir: Path,
    logs: list[dict[str, Any]],
    *,
    arxiv_records: list[dict[str, Any]] | None = None,
) -> list[str]:
    legacy_dir = Path("data/legacy_notebook") if not str(processed_dir).startswith("data/smoke") else Path("data/smoke/legacy_notebook")
    legacy_all, legacy_filtered, legacy_records = reproduce_legacy_from_arxiv_records(arxiv_records or [], cfg, legacy_dir)
    for r in legacy_records:
        r["run_id"] = run_id
    records = [*records, *legacy_records]

    df = pd.DataFrame(records)
    if df.empty:
        df = pd.DataFrame(columns=SCHEMA_COLUMNS)
    for i in range(len(df)):
        df.loc[i, "record_id"] = f"{run_id}_R{i + 1:06d}"
    for col in ["topic_class", "legacy_notebook_source", "legacy_notebook_included", "retrieval_status"]:
        if col not in df.columns:
            df[col] = pd.Series([pd.NA] * len(df), dtype="object")
    for idx, row in df.iterrows():
        scoring = score_record(row.to_dict(), cfg["relevance"])
        for key, value in scoring.items():
            df.loc[idx, key] = value
        if pd.notna(row.get("legacy_notebook_relevance_score")):
            df.loc[idx, "relevance_score"] = max(int(df.loc[idx, "relevance_score"]), int(row.get("legacy_notebook_relevance_score")))
        df.loc[idx, "topic_class"] = row.get("legacy_notebook_topic_class") or classify_record(row.to_dict(), cfg["topic_patterns"])
        for key, value in query_quality_indicators(row.to_dict()).items():
            df.loc[idx, key] = value
        if pd.isna(df.loc[idx].get("legacy_notebook_source")):
            df.loc[idx, "legacy_notebook_source"] = False
            df.loc[idx, "legacy_notebook_included"] = False
        if pd.isna(df.loc[idx].get("retrieval_status")):
            df.loc[idx, "retrieval_status"] = "retrieved"

    base_columns = list(dict.fromkeys([*cfg["exports"]["column_order"], *[c for c in df.columns if c not in cfg["exports"]["column_order"]]]))
    all_records = enforce_schema(df, base_columns)
    if not all_records.empty:
        from_date = pd.to_datetime(cfg["date_range"]["from_pub_date"], errors="coerce")
        until_date = pd.to_datetime(cfg["date_range"]["until_pub_date"], errors="coerce")
        pub_dates = pd.to_datetime(all_records["publication_date"], errors="coerce", utc=True).dt.tz_localize(None)
        mask = pub_dates.isna() | ((pub_dates >= from_date) & (pub_dates <= until_date))
        all_records = all_records.loc[mask].reset_index(drop=True)

    deduped, duplicate_groups, decisions = deduplicate_records(all_records, cfg)
    unique_records = _build_unique_records(deduped, all_records, duplicate_groups)
    relevant = unique_records[unique_records["relevance_score"].fillna(0).astype(int) >= int(cfg["relevance"]["threshold"])].copy() if not unique_records.empty else unique_records.copy()

    produced: list[str] = []
    produced.extend(write_table(all_records, processed_dir / "all_source_records"))
    produced.extend(write_table(unique_records, processed_dir / "deduplicated_records"))
    produced.extend(write_table(all_records, processed_dir / "all_retrieved_records"))
    produced.extend(write_table(unique_records, processed_dir / "all_unique_records"))
    produced.extend(write_table(relevant, processed_dir / "relevant_candidates", xlsx=True))
    duplicate_groups.to_csv(processed_dir / "duplicate_groups.csv", index=False)
    decisions.to_csv(processed_dir / "deduplication_decisions.csv", index=False)
    produced.extend([str(processed_dir / "duplicate_groups.csv"), str(processed_dir / "deduplication_decisions.csv")])
    reasons = load_screening_reasons("configs/screening_reasons.yaml")
    produced.append(create_screening_template(unique_records, processed_dir / "screening_template.xlsx", reasons))
    final_screening, final_files = build_final_screening(unique_records, processed_dir, reports_dir)
    produced.extend(final_files)
    reconciliation = reconcile_legacy(legacy_filtered, unique_records, reports_dir / "legacy_notebook_reconciliation.csv")
    produced.append(str(reports_dir / "legacy_notebook_reconciliation.csv"))

    log_df = pd.DataFrame(logs)
    if not log_df.empty:
        unique_counts = all_records.groupby(["database_scope", "query_id"]).size().to_dict()
        for i, row in log_df.iterrows():
            log_df.loc[i, "unique_records_before_cross_source_deduplication"] = unique_counts.get((row["database_scope"], row["query_id"]), 0)
    produced.extend(generate_reports(all_records, unique_records, log_df, cfg, run_id, reports_dir))
    produced.extend(_write_final_counts_reports(all_records, unique_records, final_screening, legacy_filtered, reconciliation, log_df, reports_dir, cfg, run_id))
    return produced


def _build_unique_records(deduped: pd.DataFrame, all_records: pd.DataFrame, groups: pd.DataFrame) -> pd.DataFrame:
    if deduped.empty:
        return deduped.copy()
    unique = deduped.copy()
    if groups.empty:
        groups = pd.DataFrame({"duplicate_group_id": unique["duplicate_group_id"], "record_id": unique["record_id"], "kept_record_id": unique["record_id"]})
    for idx, row in unique.iterrows():
        gid = row.get("duplicate_group_id")
        ids = groups.loc[groups["duplicate_group_id"] == gid, "record_id"].tolist()
        group = all_records[all_records["record_id"].isin(ids)] if ids else all_records[all_records["record_id"] == row.get("record_id")]
        if group.empty:
            continue
        sources = sorted(set(str(x) for x in group["database_scope"].dropna()))
        unique.loc[idx, "all_sources"] = "; ".join(sources)
        unique.loc[idx, "all_query_ids"] = "; ".join(sorted(set(str(x) for x in group["query_id"].dropna())))
        unique.loc[idx, "all_source_record_ids"] = "; ".join(sorted(set(str(x) for x in group["source_record_id"].dropna())))
        legacy_series = group["legacy_notebook_source"] if "legacy_notebook_source" in group else pd.Series([], dtype=object)
        unique.loc[idx, "legacy_notebook_source"] = any(str(v).lower() == "true" or v is True for v in legacy_series.dropna().tolist())
        unique.loc[idx, "arxiv_source"] = bool((group["database_scope"] == "arXiv").any())
        unique.loc[idx, "ieee_crossref_source"] = bool((group["database_scope"] == "IEEE").any())
        unique.loc[idx, "springer_crossref_source"] = bool((group["database_scope"] == "Springer").any())
        unique.loc[idx, "preprint_publication_link"] = bool((group["database_scope"].isin(["arXiv", "Legacy arXiv notebook"]).any()) and (group["database_scope"].isin(["IEEE", "Springer"]).any()))
        for col in ["arxiv_id", "doi_normalized", "doi", "abstract", "pdf_url", "abstract_url", "landing_page_url", "container_title"]:
            if pd.isna(unique.loc[idx].get(col)) or unique.loc[idx].get(col) in [None, ""]:
                vals = group[col].dropna().astype(str).tolist() if col in group else []
                if vals:
                    unique.loc[idx, col] = vals[0]
        legacy_scores = pd.to_numeric(group.get("legacy_notebook_relevance_score", pd.Series(dtype=float)), errors="coerce").dropna()
        if not legacy_scores.empty:
            unique.loc[idx, "legacy_notebook_relevance_score"] = int(legacy_scores.max())
        unique.loc[idx, "retrieval_status"] = "legacy_only" if bool(unique.loc[idx, "legacy_notebook_source"]) and not bool(unique.loc[idx, "arxiv_source"]) else "retrieved"
    return unique


def _write_final_counts_reports(all_records: pd.DataFrame, unique: pd.DataFrame, final: pd.DataFrame, legacy_filtered: pd.DataFrame, reconciliation: pd.DataFrame, log_df: pd.DataFrame, reports_dir: Path, cfg: dict[str, Any], run_id: str) -> list[str]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    files: list[str] = []
    counts = {
        "Original notebook filtered records": int(len(legacy_filtered)),
        "Fresh arXiv records": int((all_records["database_scope"] == "arXiv").sum()) if not all_records.empty else 0,
        "IEEE-scoped Crossref records": int((all_records["database_scope"] == "IEEE").sum()) if not all_records.empty else 0,
        "Springer-scoped Crossref records": int((all_records["database_scope"] == "Springer").sum()) if not all_records.empty else 0,
        "Total before deduplication": int(len(all_records)),
        "Total after deduplication": int(len(unique)),
        "CORE": int((final["screening_category"] == "CORE").sum()),
        "RELATED": int((final["screening_category"] == "RELATED").sum()),
        "BACKGROUND": int((final["screening_category"] == "BACKGROUND").sum()),
        "MANUAL_REVIEW": int((final["screening_category"] == "MANUAL_REVIEW").sum()),
        "EXCLUDE": int((final["screening_category"] == "EXCLUDE").sum()),
        "Primary quantum-diffusion models": int((final["count_as_quantum_diffusion_model"] == "YES").sum()),
        "Legacy records matched": int((reconciliation["final_status"] == "matched").sum()),
        "Legacy-only records": int((unique.get("retrieval_status", pd.Series(dtype=str)) == "legacy_only").sum()),
        "Queries truncated": int(log_df["truncated"].fillna(False).astype(bool).sum()) if not log_df.empty else 0,
        "Queries failed": int((log_df["status"] != "ok").sum()) if not log_df.empty and "status" in log_df else 0,
    }
    lines = ["# Search report", "", f"Run ID: `{run_id}`", f"Date range: {cfg['date_range']['from_pub_date']} to {cfg['date_range']['until_pub_date']}", "", "## Final counts"]
    lines.extend([f"- {k}: {v}" for k, v in counts.items()])
    lines.extend([
        "",
        "> Note: CORE/RELATED/BACKGROUND and 'primary quantum-diffusion models' are automated",
        "> labels applied to cross-source records before deduplication; they are screening aids,",
        "> not the final included set. Unique-candidate, included, excluded and pending counts are",
        "> produced by `apply-screening` (see reports/selection_flow.md).",
    ])
    lines.extend(["", "## Method", "arXiv was queried through the public arXiv API. IEEE-scoped and Springer-scoped records were retrieved from Crossref using DOI prefixes `10.1109` and `10.1007`, respectively. The original notebook filtered records were reproduced and included as a mandatory legacy source before deduplication."])
    (reports_dir / "search_report.md").write_text("\n".join(lines), encoding="utf-8")
    files.append(str(reports_dir / "search_report.md"))
    prisma = pd.DataFrame([
        ("records identified from original notebook", counts["Original notebook filtered records"], "observed"),
        ("records identified from fresh arXiv search", counts["Fresh arXiv records"], "observed"),
        ("records identified from IEEE-scoped Crossref", counts["IEEE-scoped Crossref records"], "observed"),
        ("records identified from Springer-scoped Crossref", counts["Springer-scoped Crossref records"], "observed"),
        ("duplicate records removed", counts["Total before deduplication"] - counts["Total after deduplication"], "computed"),
        ("records after deduplication", counts["Total after deduplication"], "computed"),
        ("records screened", counts["Total after deduplication"], "automated metadata screening"),
        ("records excluded", counts["EXCLUDE"], "automated metadata screening"),
        ("records marked for manual review", counts["MANUAL_REVIEW"], "automated metadata screening"),
        ("automated CORE labels (cross-source records, pre-deduplication)", counts["CORE"], "automated metadata screening"),
        ("records included as RELATED", counts["RELATED"], "automated metadata screening"),
        ("records included as BACKGROUND", counts["BACKGROUND"], "automated metadata screening"),
        ("automated CORE candidates for manual screening (cross-source)", counts["Primary quantum-diffusion models"], "screening aid, not final inclusion"),
    ], columns=["prisma_item", "count", "status"])
    prisma.to_csv(reports_dir / "prisma_flow_counts.csv", index=False)
    files.append(str(reports_dir / "prisma_flow_counts.csv"))
    return files


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
    from .reproduce import reproduce_run

    return reproduce_run(raw_run)


if __name__ == "__main__":
    raise SystemExit(main())
