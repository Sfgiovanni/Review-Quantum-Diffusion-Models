"""Report generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd


def generate_reports(
    all_records: pd.DataFrame,
    deduped: pd.DataFrame,
    search_log: pd.DataFrame,
    cfg: dict[str, Any],
    run_id: str,
    reports_dir: Path,
) -> list[str]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "tables").mkdir(exist_ok=True)
    (reports_dir / "figures").mkdir(exist_ok=True)
    files: list[str] = []
    files.append(_write_search_log(search_log, reports_dir / "search_log.csv"))
    files.append(_write_prisma(all_records, deduped, search_log, reports_dir / "prisma_flow_counts.csv"))
    files.extend(_write_figures(deduped, reports_dir / "figures"))
    files.append(_write_markdown_report(all_records, deduped, search_log, cfg, run_id, reports_dir / "search_report.md"))
    files.append(_write_methods_text(deduped, cfg, run_id, reports_dir / "methods_text.md"))
    summary = {
        "run_id": run_id,
        "raw_records": int(len(all_records)),
        "deduplicated_records": int(len(deduped)),
        "relevant_candidates": int((deduped["relevance_score"].fillna(0).astype(int) >= int(cfg["relevance"]["threshold"])).sum()) if not deduped.empty else 0,
        "truncated_queries": int(search_log["truncated"].fillna(False).sum()) if not search_log.empty else 0,
        "failed_queries": int((search_log["status"] != "ok").sum()) if not search_log.empty and "status" in search_log else 0,
    }
    path = reports_dir / "run_summary.json"
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    files.append(str(path))
    return files


def _write_search_log(df: pd.DataFrame, path: Path) -> str:
    df.to_csv(path, index=False)
    return str(path)


def _write_prisma(all_records: pd.DataFrame, deduped: pd.DataFrame, search_log: pd.DataFrame, path: Path) -> str:
    counts = [
        ("records identified from arXiv", _count_scope(all_records, "arXiv"), "observed"),
        ("records identified from IEEE-scoped Crossref search", _count_scope(all_records, "IEEE"), "observed"),
        ("records identified from Springer-scoped Crossref search", _count_scope(all_records, "Springer"), "observed"),
        ("duplicate records removed", max(len(all_records) - len(deduped), 0), "computed"),
        ("records marked for manual duplicate review", None, "pending"),
        ("records after deduplication", len(deduped), "computed"),
        ("records screened", None, "pending"),
        ("records excluded", None, "pending"),
        ("full-text reports sought", None, "pending"),
        ("full-text reports assessed", None, "pending"),
        ("studies included", None, "pending"),
    ]
    pd.DataFrame(counts, columns=["prisma_item", "count", "status"]).to_csv(path, index=False)
    return str(path)


def _count_scope(df: pd.DataFrame, scope: str) -> int:
    return int((df["database_scope"] == scope).sum()) if not df.empty and "database_scope" in df else 0


def _write_figures(df: pd.DataFrame, fig_dir: Path) -> list[str]:
    files = []
    for col, name in [("year", "records_by_year"), ("document_type", "records_by_document_type")]:
        if df.empty or col not in df:
            continue
        counts = df[col].dropna().astype(str).value_counts().sort_index()
        if counts.empty:
            continue
        ax = counts.plot(kind="bar", figsize=(8, 4))
        ax.set_xlabel(col.replace("_", " ").title())
        ax.set_ylabel("Records")
        plt.tight_layout()
        for suffix in [".png", ".svg"]:
            path = fig_dir / f"{name}{suffix}"
            plt.savefig(path)
            files.append(str(path))
        plt.close()
    return files


def _write_markdown_report(all_records: pd.DataFrame, deduped: pd.DataFrame, log: pd.DataFrame, cfg: dict[str, Any], run_id: str, path: Path) -> str:
    threshold = int(cfg["relevance"]["threshold"])
    relevant = deduped[deduped["relevance_score"].fillna(0).astype(int) >= threshold] if not deduped.empty else deduped
    lines = [
        "# Search report",
        "",
        f"Run ID: `{run_id}`",
        f"Search date: {cfg['date_range']['until_pub_date']}",
        f"Temporal range: {cfg['date_range']['from_pub_date']} to {cfg['date_range']['until_pub_date']}",
        "",
        "## Sources and retrieval methods",
        "- arXiv: public arXiv API.",
        "- IEEE scope: Crossref REST API restricted to DOI prefix `10.1109`.",
        "- Springer scope: Crossref REST API restricted to DOI prefix `10.1007`.",
        "",
        "The IEEE- and Springer-scoped records are Crossref metadata records, not direct results from IEEE Xplore or Springer Nature proprietary APIs.",
        "",
        "## Counts",
        f"- Records before cross-source deduplication: {len(all_records)}",
        f"- Records after deduplication: {len(deduped)}",
        f"- Records above relevance threshold ({threshold}): {len(relevant)}",
        f"- Queries truncated: {int(log['truncated'].fillna(False).sum()) if not log.empty else 0}",
        f"- Failed or incomplete queries: {int((log['status'] != 'ok').sum()) if not log.empty and 'status' in log else 0}",
        "",
        "## Queries",
    ]
    for q in cfg["queries"]:
        lines.append(f"- `{q['query_id']}` {q['concept']}: arXiv `{q['arxiv_query']}`; Crossref `{q['crossref_query']}`")
    if not deduped.empty:
        lines.extend(["", "## Topic distribution", deduped["topic_class"].fillna("missing").value_counts().to_markdown()])
    lines.extend(
        [
            "",
            "## Limitations",
            "Crossref abstracts are often incomplete or absent. DOI-prefix scoping does not equal a direct search of proprietary IEEE Xplore or Springer Nature APIs. Automated scoring is only a prioritization aid and final inclusion requires human screening.",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def _write_methods_text(deduped: pd.DataFrame, cfg: dict[str, Any], run_id: str, path: Path) -> str:
    text = f"""# Methods text

On {cfg['date_range']['until_pub_date']}, we executed a predefined reproducible search strategy for quantum diffusion model literature (run `{run_id}`). The public arXiv API was queried directly. IEEE-scoped and Springer-scoped metadata were retrieved from the Crossref REST API using DOI-prefix restrictions, with IEEE delimited by `10.1109` and Springer delimited by `10.1007`; these records should not be interpreted as direct programmatic searches of IEEE Xplore or Springer Nature proprietary APIs. Searches used predefined query strings and the publication-date interval {cfg['date_range']['from_pub_date']} to {cfg['date_range']['until_pub_date']}. Raw API responses and request parameters were preserved. Records were normalized to a common schema and duplicates were identified using DOI, arXiv identifiers, normalized titles, publication years, and author evidence while preserving source provenance. A deterministic heuristic relevance score was computed only to prioritize manual screening. Final study inclusion remains dependent on human title/abstract and full-text screening. The run produced {len(deduped)} deduplicated records.
"""
    path.write_text(text, encoding="utf-8")
    return str(path)
