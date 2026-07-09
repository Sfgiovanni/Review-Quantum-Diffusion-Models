"""Layered conservative deduplication with provenance preservation."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd
from rapidfuzz import fuzz


def _same_year(a: Any, b: Any, tolerance: int) -> bool:
    try:
        return abs(int(a) - int(b)) <= tolerance
    except (TypeError, ValueError):
        return False


def deduplicate_records(df: pd.DataFrame, cfg: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return df.copy(), pd.DataFrame(), pd.DataFrame()
    work = df.copy().reset_index(drop=True)
    parent = list(range(len(work)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    decisions: list[dict[str, Any]] = []

    def union(i: int, j: int, rule: str, score: float | None, auto: bool = True) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri
        decisions.append(
            {
                "record_id_a": work.loc[i, "record_id"],
                "record_id_b": work.loc[j, "record_id"],
                "rule": rule,
                "similarity_score": score,
                "kept_record_id": work.loc[ri, "record_id"],
                "merged_record_id": work.loc[j, "record_id"],
                "decision": "automatic_merge" if auto else "manual_review_candidate",
                "conflicting_fields": _conflicts(work.loc[i], work.loc[j]),
            }
        )

    for _, group in work.dropna(subset=["doi_normalized"]).groupby("doi_normalized"):
        idx = list(group.index)
        for j in idx[1:]:
            union(idx[0], j, "doi_normalized", 100)

    for i, a in work.iterrows():
        if not a.get("doi_normalized") or not a.get("container_title"):
            continue
        for j, b in work.iloc[i + 1 :].iterrows():
            if a.get("doi_normalized") == b.get("doi_normalized"):
                continue
            if a.get("title_normalized") and a.get("title_normalized") == b.get("title_normalized") and _same_year(a.get("year"), b.get("year"), 1):
                union(i, j, "arxiv_publication_title_journal_ref", 100)

    tolerance = int(cfg["deduplication"].get("year_tolerance", 1))
    for _, group in work.dropna(subset=["title_normalized"]).groupby("title_normalized"):
        idx = list(group.index)
        for j in idx[1:]:
            if _same_year(work.loc[idx[0], "year"], work.loc[j, "year"], tolerance):
                union(idx[0], j, "exact_normalized_title_year", 100)

    candidate_threshold = int(cfg["deduplication"].get("title_similarity_candidate_threshold", 94))
    auto_threshold = int(cfg["deduplication"].get("title_similarity_auto_threshold", 98))
    for i, a in work.iterrows():
        title_a = a.get("title_normalized")
        if not title_a:
            continue
        for j, b in work.iloc[i + 1 :].iterrows():
            title_b = b.get("title_normalized")
            if not title_b or find(i) == find(j) or not _same_year(a.get("year"), b.get("year"), tolerance):
                continue
            score = fuzz.token_sort_ratio(title_a, title_b)
            if score >= auto_threshold and _author_overlap(a.get("authors"), b.get("authors")):
                union(i, j, "conservative_fuzzy_title_author_year", score)
            elif score >= candidate_threshold:
                decisions.append(
                    {
                        "record_id_a": a["record_id"],
                        "record_id_b": b["record_id"],
                        "rule": "fuzzy_title_candidate",
                        "similarity_score": score,
                        "kept_record_id": None,
                        "merged_record_id": None,
                        "decision": "manual_review_candidate",
                        "conflicting_fields": _conflicts(a, b),
                    }
                )

    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(len(work)):
        groups[find(i)].append(i)

    dedup_rows = []
    group_rows = []
    for n, idxs in enumerate(groups.values(), start=1):
        group_id = f"D{n:05d}"
        group = work.loc[idxs]
        kept = _choose_kept(group)
        merged_sources = sorted(set(str(x) for x in group["database_scope"].dropna()))
        row = kept.to_dict()
        row["duplicate_group_id"] = group_id
        row["merged_sources"] = "; ".join(merged_sources)
        dedup_rows.append(row)
        for _, r in group.iterrows():
            group_rows.append(
                {
                    "duplicate_group_id": group_id,
                    "record_id": r["record_id"],
                    "kept_record_id": kept["record_id"],
                    "database_scope": r.get("database_scope"),
                    "doi_normalized": r.get("doi_normalized"),
                    "title_normalized": r.get("title_normalized"),
                }
            )
    return pd.DataFrame(dedup_rows), pd.DataFrame(group_rows), pd.DataFrame(decisions)


def _author_overlap(a: Any, b: Any) -> bool:
    sa = {x.strip().lower() for x in str(a or "").split(";") if x.strip()}
    sb = {x.strip().lower() for x in str(b or "").split(";") if x.strip()}
    return bool(sa and sb and sa.intersection(sb))


def _conflicts(a: pd.Series, b: pd.Series) -> str | None:
    fields = ["title", "year", "doi_normalized", "container_title", "publisher"]
    conflicts = [f for f in fields if pd.notna(a.get(f)) and pd.notna(b.get(f)) and a.get(f) != b.get(f)]
    return "; ".join(conflicts) or None


def _choose_kept(group: pd.DataFrame) -> pd.Series:
    order = {"Crossref": 0, "arXiv API": 1}
    ranked = group.copy()
    ranked["_rank"] = ranked["retrieval_source"].map(order).fillna(9)
    ranked["_has_doi"] = ranked["doi_normalized"].notna().map({True: 0, False: 1})
    return ranked.sort_values(["_has_doi", "_rank", "record_id"]).iloc[0].drop(labels=["_rank", "_has_doi"])
