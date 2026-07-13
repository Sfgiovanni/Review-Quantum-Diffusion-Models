"""Apply manual screening decisions to the automated candidate pool (all years).

Turns the human screening spreadsheet into the explicit, auditable selection flow
required for a systematic review::

    all-source CORE (with cross-source duplicates)
      -> unique CORE candidates (after deduplication)
      -> manually screened (all years)
      -> included (CORE) / related (RELATED) / pending (MANUAL_REVIEW) / excluded (EXCLUDE)

The review corpus is the full field across all years; the last narrative review
(early 2025) is superseded here by a systematic, reproducible protocol extended to
mid-2026. The spreadsheet uses the standard screening vocabulary
(CORE / RELATED / BACKGROUND / MANUAL_REVIEW / EXCLUDE); the analyst verbs
(INCLUDE / EXCLUDE / MAYBE) are also accepted for backward compatibility.

Nothing is invented: every included study comes from an explicit CORE row. Studies
screened but absent from the automated pool are reported separately, so "retrieved
automatically" and "added by hand" never collapse into one number.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import pandas as pd

DECISION_CANON = {
    "CORE": "included",
    "INCLUDE": "included",
    "INCLUDED": "included",
    "RELATED": "related",
    "EXCLUDE": "excluded",
    "EXCLUDED": "excluded",
    "MANUAL_REVIEW": "pending",
    "MAYBE": "pending",
    "PENDING": "pending",
    "BACKGROUND": "background",
    "HISTORICAL": "background",
}

_PRIMARY = {"included", "related", "excluded", "pending"}
_ARXIV_VERSION = re.compile(r"v\d+$")


def _norm_arxiv(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return _ARXIV_VERSION.sub("", str(value).strip().lower().replace("arxiv:", ""))


def _norm_doi(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip().lower().replace("https://doi.org/", "").replace("doi:", "")


def _read_csv(path: Path) -> "pd.DataFrame | None":
    if path.exists():
        return pd.read_csv(path, dtype=str, keep_default_na=False, engine="python", on_bad_lines="skip")
    return None


def _match_key(df: pd.DataFrame) -> pd.Series:
    n = len(df)
    arx = df["arxiv_id"] if "arxiv_id" in df.columns else pd.Series([""] * n, index=df.index)
    if "doi_normalized" in df.columns:
        doi = df["doi_normalized"]
    elif "doi" in df.columns:
        doi = df["doi"]
    else:
        doi = pd.Series([""] * n, index=df.index)
    key = arx.map(_norm_arxiv)
    return key.where(key != "", doi.map(_norm_doi))


def apply_screening(
    screening_csv: Path,
    processed_dir: Path = Path("data/processed"),
    reports_dir: Path = Path("reports"),
    corpus_from: "int | None" = None,
    corpus_to: "int | None" = None,
) -> dict[str, Any]:
    manual = pd.read_csv(screening_csv, dtype=str, keep_default_na=False)
    decision_col = "screening_category" if "screening_category" in manual.columns else "screening_decision"
    if decision_col not in manual.columns:
        raise ValueError("manual screening file must contain 'screening_category' or 'screening_decision'")
    manual["decision"] = manual[decision_col].str.strip().str.upper().map(DECISION_CANON)
    unknown = manual.loc[manual["decision"].isna(), decision_col].unique().tolist()
    if unknown:
        raise ValueError(f"Unknown {decision_col} values: {unknown}")
    manual["match_key"] = _match_key(manual)

    # The human-screened universe is the automated shortlist: CORE + RELATED +
    # MANUAL_REVIEW (NOT relevant_candidates, which is the broad relevance filter).
    frames = []
    for name in ["papers_core.csv", "papers_related.csv", "papers_manual_review.csv"]:
        part = _read_csv(processed_dir / name)
        if part is not None:
            frames.append(part)
    if frames:
        pool = pd.concat(frames, ignore_index=True)
    else:
        pool = _read_csv(processed_dir / "relevant_candidates.csv")
        if pool is None:
            pool = _read_csv(processed_dir / "deduplicated_records.csv")
    if pool is None:
        raise FileNotFoundError("No candidate pool found (papers_core.csv / relevant_candidates.csv / deduplicated_records.csv)")
    pool["match_key"] = _match_key(pool)
    pool_keys = set(pool["match_key"]) - {""}

    meta_cols = [c for c in ["record_id", "run_id", "year", "title", "first_author", "topic_class"] if c in pool.columns]
    enriched = manual.merge(pool[["match_key", *meta_cols]], on="match_key", how="left", suffixes=("", "_pool"))
    for col in ["year", "title", "record_id", "run_id"]:
        pool_col = f"{col}_pool"
        if pool_col in enriched.columns:
            base = enriched[col] if col in enriched.columns else pd.Series([""] * len(enriched))
            enriched[col] = base.replace("", pd.NA).fillna(enriched[pool_col])
    enriched["in_automated_pool"] = enriched["match_key"].isin(pool_keys)
    enriched["year_int"] = pd.to_numeric(enriched.get("year"), errors="coerce")

    if corpus_from is None and corpus_to is None:
        in_window = pd.Series(True, index=enriched.index)
    else:
        lo = corpus_from if corpus_from is not None else -10_000
        hi = corpus_to if corpus_to is not None else 10_000
        in_window = enriched["year_int"].between(lo, hi)

    def _stage(mask: pd.Series) -> pd.DataFrame:
        cols = [c for c in ["record_id", "run_id", "arxiv_id", "doi", "year", "title", "decision",
                            decision_col, "exclusion_reason", "family", "generated_object",
                            "in_automated_pool", "notes"] if c in enriched.columns]
        return enriched.loc[mask, cols].reset_index(drop=True)

    included = _stage((enriched["decision"] == "included") & in_window)
    related = _stage((enriched["decision"] == "related") & in_window)
    pending = _stage((enriched["decision"] == "pending") & in_window)
    excluded = _stage((enriched["decision"] == "excluded") & in_window)
    background = _stage(enriched["decision"] == "background")
    evaluated = _stage(enriched["decision"].isin(_PRIMARY) & in_window)
    main_corpus = included
    historical = _stage((enriched["decision"] == "background") | (enriched["decision"].isin(_PRIMARY) & ~in_window))
    dedup_cols = [c for c in ["arxiv_id", "doi"] if c in historical.columns]
    if dedup_cols:
        historical = historical.drop_duplicates(subset=dedup_cols).reset_index(drop=True)
    manually_added = _stage(enriched["decision"].isin(_PRIMARY) & ~enriched["in_automated_pool"])

    all_src = _read_csv(processed_dir / "all_source_records.csv")
    core_source = None
    if all_src is not None:
        all_src["match_key"] = _match_key(all_src)
        core_source = all_src[all_src["match_key"].isin(pool_keys)].reset_index(drop=True)

    processed_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, pd.DataFrame] = {
        "core_unique_candidates.csv": pool.drop(columns=["match_key"], errors="ignore"),
        "screened_candidates.csv": evaluated,
        "included_studies.csv": included,
        "related_studies.csv": related,
        "pending_studies.csv": pending,
        "excluded_studies.csv": excluded,
        "main_corpus.csv": main_corpus,
        "manually_added_studies.csv": manually_added,
    }
    if len(historical):
        outputs["historical_background.csv"] = historical
    if core_source is not None:
        outputs["core_source_records.csv"] = core_source.drop(columns=["match_key"], errors="ignore")
    for name, frame in outputs.items():
        frame.to_csv(processed_dir / name, index=False)

    upstream = _load_upstream_counts(reports_dir)
    prisma_rows: list[tuple[str, int, str]] = []
    if upstream.get("all_sources") is not None:
        prisma_rows.append(("records identified (all sources, with cross-source duplicates)", upstream["all_sources"], "observed"))
    if upstream.get("after_dedup") is not None:
        prisma_rows.append(("unique records after deduplication", upstream["after_dedup"], "computed"))
    if core_source is not None:
        prisma_rows.append(("automated CORE candidates (cross-source, pre-deduplication)", len(core_source), "recomputed"))
    elif upstream.get("core_cross_source") is not None:
        prisma_rows.append(("automated CORE candidates (cross-source, pre-deduplication)", upstream["core_cross_source"], "carried"))
    prisma_rows.extend([
        ("unique CORE candidates after deduplication", len(pool), "computed"),
        ("manually screened (all years)", len(evaluated), "manual screening"),
        ("manually added beyond automated pool", len(manually_added), "manual screening"),
        ("included studies (CORE)", len(included), "manual screening"),
        ("related studies (RELATED)", len(related), "manual screening"),
        ("pending / manual review", len(pending), "manual screening"),
        ("excluded studies (EXCLUDE)", len(excluded), "manual screening"),
        ("review corpus (all years)", len(main_corpus), "computed"),
    ])
    prisma = pd.DataFrame(prisma_rows, columns=["prisma_item", "count", "status"]).drop_duplicates("prisma_item", keep="last")
    prisma.to_csv(reports_dir / "prisma_flow_counts.csv", index=False)
    _write_flow_report(reports_dir, prisma, manually_added)

    return {
        "core_unique_candidates": len(pool),
        "manually_screened": len(evaluated),
        "included": len(included),
        "related": len(related),
        "pending": len(pending),
        "excluded": len(excluded),
        "background": len(background),
        "review_corpus": len(main_corpus),
        "manually_added_beyond_pool": len(manually_added),
    }


def _load_upstream_counts(reports_dir: Path) -> dict[str, "int | None"]:
    out: dict[str, "int | None"] = {"all_sources": None, "after_dedup": None, "core_cross_source": None}
    path = reports_dir / "prisma_flow_counts.csv"
    if not path.exists():
        return out
    try:
        df = pd.read_csv(path)
    except Exception:
        return out

    def _num(x):
        try:
            return int(x)
        except (TypeError, ValueError):
            return None

    lut = {str(k).strip().lower(): _num(v) for k, v in zip(df["prisma_item"], df["count"])}
    out["after_dedup"] = lut.get("records after deduplication") or lut.get("unique records after deduplication")
    out["core_cross_source"] = (
        lut.get("records included as core")
        or lut.get("automated core candidates (cross-source, pre-deduplication)")
    )
    out["all_sources"] = (
        lut.get("total before deduplication")
        or lut.get("records identified (all sources, with cross-source duplicates)")
    )
    if out["all_sources"] is None and lut.get("duplicate records removed") is not None and out["after_dedup"] is not None:
        out["all_sources"] = lut["duplicate records removed"] + out["after_dedup"]
    return out


def _write_flow_report(reports_dir: Path, prisma: pd.DataFrame, manually_added: pd.DataFrame) -> None:
    lines = ["# Selection flow (manual screening applied, all years)", ""]
    for _, row in prisma.iterrows():
        lines.append(f"- {row['prisma_item']}: {row['count']}")
    if len(manually_added):
        lines += ["", "## Studies added manually beyond the automated pool",
                  "Included by expert screening but not surfaced by the automated search.",
                  "The circuit-synthesis queries (Q19-Q23) added to the search config are intended",
                  "to retrieve these on the next run.", ""]
        for _, row in manually_added.iterrows():
            lines.append(f"- {row.get('arxiv_id', '')} - {row.get('title', '')}")
    (reports_dir / "selection_flow.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(prog="quantum_diffusion_search apply-screening")
    parser.add_argument("--screening", default="data/screening/manual_screening.csv")
    parser.add_argument("--processed", default="data/processed")
    parser.add_argument("--reports", default="reports")
    parser.add_argument("--corpus-from", type=int, default=None, help="optional lower year bound (default: all years)")
    parser.add_argument("--corpus-to", type=int, default=None, help="optional upper year bound (default: all years)")
    args = parser.parse_args(argv)
    summary = apply_screening(Path(args.screening), Path(args.processed), Path(args.reports),
                              corpus_from=args.corpus_from, corpus_to=args.corpus_to)
    width = max(len(k) for k in summary)
    for key, value in summary.items():
        print(f"{key.ljust(width)} : {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
