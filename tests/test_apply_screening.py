"""Deterministic mechanics test for the manual-screening stage (all years)."""

from pathlib import Path

import pandas as pd

from quantum_diffusion_search.apply_screening import apply_screening


def _setup(tmp_path: Path):
    proc = tmp_path / "data" / "processed"
    proc.mkdir(parents=True)
    reports = tmp_path / "reports"
    reports.mkdir()
    screening = tmp_path / "data" / "screening"
    screening.mkdir(parents=True)
    pd.DataFrame([
        {"record_id": "R1", "arxiv_id": "2501.00001", "doi": "", "year": "2025", "title": "A", "relevance_score": "30"},
        {"record_id": "R2", "arxiv_id": "2506.00002", "doi": "", "year": "2025", "title": "B", "relevance_score": "20"},
        {"record_id": "R3", "arxiv_id": "2301.00003", "doi": "", "year": "2023", "title": "C", "relevance_score": "25"},
    ]).to_csv(proc / "relevant_candidates.csv", index=False)
    pd.DataFrame([
        {"arxiv_id": "2501.00001", "year": "2025", "title": "A", "screening_category": "CORE", "exclusion_reason": ""},
        {"arxiv_id": "2506.00002", "year": "2025", "title": "B", "screening_category": "EXCLUDE", "exclusion_reason": "off-topic"},
        {"arxiv_id": "2301.00003", "year": "2023", "title": "C", "screening_category": "RELATED", "exclusion_reason": ""},
        {"arxiv_id": "2505.09999", "year": "2025", "title": "Z", "screening_category": "CORE", "exclusion_reason": ""},
    ]).to_csv(screening / "manual_screening.csv", index=False)
    return proc, reports, screening


def test_flow_mechanics(tmp_path):
    proc, reports, screening = _setup(tmp_path)
    s = apply_screening(screening / "manual_screening.csv", proc, reports)
    assert s["core_unique_candidates"] == 3
    assert s["included"] == 2                    # A + Z (both CORE)
    assert s["related"] == 1                     # C
    assert s["excluded"] == 1                    # B
    assert s["pending"] == 0
    assert s["manually_screened"] == 4           # A, B, C, Z (all primary)
    assert s["review_corpus"] == 2               # CORE across all years
    assert s["manually_added_beyond_pool"] == 1  # Z not in pool
    for name in ["included_studies.csv", "related_studies.csv", "excluded_studies.csv",
                 "main_corpus.csv", "manually_added_studies.csv"]:
        assert (proc / name).exists()
    items = set(pd.read_csv(reports / "prisma_flow_counts.csv")["prisma_item"])
    assert "included studies (CORE)" in items
    assert "review corpus (all years)" in items
