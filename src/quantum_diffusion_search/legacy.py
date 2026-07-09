"""Reproduce and reconcile the original arXiv notebook output."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from rapidfuzz import fuzz

from .normalization import normalize_doi, normalize_title, strip_arxiv_version


def reproduce_legacy_from_arxiv_records(arxiv_records: list[dict[str, Any]], cfg: dict[str, Any], output_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, Any]]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in arxiv_records:
        rows.append(
            {
                "search_query": r.get("query_text"),
                "arxiv_id": r.get("arxiv_id"),
                "arxiv_id_base": strip_arxiv_version(r.get("arxiv_id")),
                "title": r.get("title"),
                "authors": str(r.get("authors") or "").replace(";", ","),
                "published": r.get("publication_date"),
                "updated": r.get("updated_date"),
                "year": r.get("year"),
                "primary_category": (str(r.get("categories") or "").split(";")[0].strip() or None),
                "categories": str(r.get("categories") or "").replace(";", ","),
                "summary": r.get("abstract"),
                "comment": None,
                "journal_ref": r.get("container_title"),
                "doi": r.get("doi"),
                "abs_url": r.get("abstract_url") or r.get("landing_page_url"),
                "pdf_url": r.get("pdf_url"),
                "legacy_notebook_query": r.get("query_text"),
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        df_all = df
        df_filtered = df
    else:
        df = df.drop_duplicates(subset=["arxiv_id_base"]).copy()
        df = df[df["year"].fillna(0).astype(int) >= 2020].copy()
        df["relevance_score"] = df.apply(lambda row: legacy_relevance_score(row.get("title"), row.get("summary"), row.get("categories")), axis=1)
        df["topic_class"] = df.apply(lambda row: legacy_classify_topic(row.get("title"), row.get("summary")), axis=1)
        df_all = df.sort_values("published", ascending=False).reset_index(drop=True)
        df_filtered = df_all[df_all["relevance_score"] >= 6].copy().sort_values(["relevance_score", "published"], ascending=[False, False]).reset_index(drop=True)
    df_all.to_csv(output_dir / "arxiv_original_all.csv", index=False)
    df_filtered.to_csv(output_dir / "arxiv_original_filtered.csv", index=False)
    df_filtered.to_excel(output_dir / "arxiv_original_filtered.xlsx", index=False)
    legacy_records = [legacy_row_to_record(row, cfg) for _, row in df_filtered.iterrows()]
    return df_all, df_filtered, legacy_records


POSITIVE_PATTERNS = {
    r"\bdiffusion model(s)?\b": 6,
    r"\bdenoising diffusion\b": 7,
    r"\bdenoising diffusion probabilistic model(s)?\b": 8,
    r"\bddpm\b": 6,
    r"\bscore[- ]based\b": 6,
    r"\bscore matching\b": 5,
    r"\bgenerative model(s)?\b": 4,
    r"\bquantum generative\b": 6,
    r"\bquantum machine learning\b": 4,
    r"\bquantum neural network(s)?\b": 4,
    r"\bquantum circuit(s)?\b": 3,
    r"\bvariational quantum\b": 3,
    r"\bstochastic schr[oö]dinger diffusion\b": 8,
    r"\bschr[oö]dinger bridge\b": 4,
    r"\bdensity matrix\b": 2,
    r"\bopen quantum system(s)?\b": 2,
}
NEGATIVE_PATTERNS = {
    r"\bspin diffusion\b": -5,
    r"\bcharge diffusion\b": -5,
    r"\bthermal diffusion\b": -5,
    r"\bneutron diffusion\b": -5,
    r"\bparticle diffusion\b": -4,
    r"\bsubdiffusion\b": -3,
    r"\banderson localization\b": -3,
    r"\bquantum walk(s)?\b": -2,
}


def legacy_relevance_score(title: Any, summary: Any, categories: Any = "") -> int:
    import re

    text = f"{title or ''} {summary or ''} {categories or ''}".lower()
    score = 0
    if "quantum" in text:
        score += 3
    if "diffusion" in text:
        score += 3
    for pattern, weight in POSITIVE_PATTERNS.items():
        if re.search(pattern, text):
            score += weight
    for pattern, penalty in NEGATIVE_PATTERNS.items():
        if re.search(pattern, text):
            score += penalty
    return score


def legacy_classify_topic(title: Any, summary: Any) -> str:
    import re

    text = f"{title or ''} {summary or ''}".lower()
    if re.search(r"denoising diffusion|ddpm", text):
        return "DDPM / denoising diffusion"
    if re.search(r"score[- ]based|score matching", text):
        return "score-based diffusion"
    if re.search(r"stochastic schr[oö]dinger diffusion", text):
        return "stochastic Schrödinger diffusion"
    if re.search(r"schr[oö]dinger bridge", text):
        return "Schrödinger bridge"
    if re.search(r"quantum circuit|variational quantum|quantum neural network", text):
        return "quantum circuit / QNN generative model"
    if re.search(r"quantum generative", text):
        return "quantum generative model"
    return "other / needs manual check"


def legacy_row_to_record(row: pd.Series, cfg: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": None,
        "database_scope": "Legacy arXiv notebook",
        "retrieval_source": "Original notebook reproduction",
        "retrieval_method": "Reproduced original arXiv notebook logic",
        "query_id": "LEGACY",
        "query_text": row.get("legacy_notebook_query") or row.get("search_query"),
        "source_record_id": row.get("arxiv_id_base"),
        "title": row.get("title"),
        "title_normalized": normalize_title(row.get("title")),
        "abstract": row.get("summary"),
        "authors": str(row.get("authors") or "").replace(",", ";"),
        "first_author": str(row.get("authors") or "").split(",")[0].strip() or None,
        "publication_date": row.get("published"),
        "year": row.get("year"),
        "updated_date": row.get("updated"),
        "doi": row.get("doi"),
        "doi_normalized": normalize_doi(row.get("doi")),
        "arxiv_id": row.get("arxiv_id_base"),
        "publisher": "arXiv",
        "container_title": row.get("journal_ref"),
        "document_type": "preprint",
        "categories": row.get("categories"),
        "abstract_url": row.get("abs_url"),
        "pdf_url": row.get("pdf_url"),
        "landing_page_url": row.get("abs_url"),
        "raw_source_file": "data/legacy_notebook/arxiv_original_filtered.csv",
        "retrieved_at_utc": None,
        "publisher_validation": "valid",
        "publisher_validation_reason": "Included because it appears in the reproduced filtered output of the original notebook.",
        "screening_status": "not_screened",
        "legacy_notebook_source": True,
        "legacy_notebook_included": True,
        "legacy_notebook_relevance_score": row.get("relevance_score"),
        "legacy_notebook_topic_class": row.get("topic_class"),
        "legacy_notebook_query": row.get("legacy_notebook_query") or row.get("search_query"),
        "retrieval_status": "legacy_reproduced",
    }


def reconcile_legacy(legacy_filtered: pd.DataFrame, unique_records: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    rows = []
    for _, legacy in legacy_filtered.iterrows():
        matched = _match_legacy_row(legacy, unique_records)
        rows.append({
            "legacy_title": legacy.get("title"),
            "legacy_arxiv_id": legacy.get("arxiv_id_base"),
            "legacy_doi": normalize_doi(legacy.get("doi")),
            "legacy_year": legacy.get("year"),
            "found_in_new_arxiv_search": bool(matched.get("arxiv_source", False)) if matched else False,
            "found_in_ieee": bool(matched.get("ieee_crossref_source", False)) if matched else False,
            "found_in_springer": bool(matched.get("springer_crossref_source", False)) if matched else False,
            "matched_record_id": matched.get("record_id") if matched else None,
            "match_method": matched.get("match_method") if matched else None,
            "match_confidence": matched.get("match_confidence") if matched else 0,
            "final_status": "matched" if matched else "missing",
            "notes": matched.get("notes") if matched else "Legacy filtered record was not found in the consolidated dataset.",
        })
    df = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return df


def _match_legacy_row(legacy: pd.Series, unique: pd.DataFrame) -> dict[str, Any] | None:
    arxiv_id = strip_arxiv_version(legacy.get("arxiv_id_base"))
    doi = normalize_doi(legacy.get("doi"))
    title_norm = normalize_title(legacy.get("title"))
    authors = str(legacy.get("authors") or "").lower()
    if arxiv_id and "arxiv_id" in unique:
        m = unique[unique["arxiv_id"].fillna("").astype(str).str.replace(r"v\d+$", "", regex=True) == arxiv_id]
        if not m.empty:
            return _matched(m.iloc[0], "arxiv_id", 1.0)
    if doi and "doi_normalized" in unique:
        m = unique[unique["doi_normalized"].fillna("") == doi]
        if not m.empty:
            return _matched(m.iloc[0], "doi", 1.0)
    if title_norm and "title_normalized" in unique:
        m = unique[unique["title_normalized"].fillna("") == title_norm]
        if not m.empty:
            return _matched(m.iloc[0], "title_normalized", 0.95)
    best = None
    best_score = 0
    for _, row in unique.iterrows():
        t = row.get("title_normalized")
        if not title_norm or not t:
            continue
        score = fuzz.token_sort_ratio(title_norm, t) / 100
        author_bonus = 0.03 if authors and any(a.strip().lower() in str(row.get("authors") or "").lower() for a in authors.split(",")[:2] if a.strip()) else 0
        total = score + author_bonus
        if total > best_score:
            best_score = total
            best = row
    if best is not None and best_score >= 0.93:
        return _matched(best, "conservative_fuzzy_title_author", round(min(best_score, 0.99), 3))
    return None


def _matched(row: pd.Series, method: str, confidence: float) -> dict[str, Any]:
    out = row.to_dict()
    out["match_method"] = method
    out["match_confidence"] = confidence
    out["notes"] = "Matched against consolidated unique dataset."
    return out
