import pandas as pd

from quantum_diffusion_search.config import load_config
from quantum_diffusion_search.deduplication import deduplicate_records


def test_deduplicate_by_doi():
    cfg = load_config("configs/search_config.yaml")
    df = pd.DataFrame(
        [
            {"record_id": "a", "doi_normalized": "10.1109/x", "title_normalized": "quantum diffusion", "year": 2024, "retrieval_source": "Crossref", "database_scope": "IEEE"},
            {"record_id": "b", "doi_normalized": "10.1109/x", "title_normalized": "quantum diffusion", "year": 2024, "retrieval_source": "arXiv API", "database_scope": "arXiv"},
        ]
    )
    deduped, groups, decisions = deduplicate_records(df, cfg)
    assert len(deduped) == 1
    assert len(groups) == 2
    assert "doi_normalized" in decisions["rule"].iloc[0]


def test_deduplicate_by_exact_title_year():
    cfg = load_config("configs/search_config.yaml")
    df = pd.DataFrame(
        [
            {"record_id": "a", "doi_normalized": None, "title_normalized": "quantum diffusion", "year": 2024, "retrieval_source": "Crossref", "database_scope": "IEEE"},
            {"record_id": "b", "doi_normalized": None, "title_normalized": "quantum diffusion", "year": 2025, "retrieval_source": "arXiv API", "database_scope": "arXiv"},
        ]
    )
    deduped, _, decisions = deduplicate_records(df, cfg)
    assert len(deduped) == 1
    assert "exact_normalized_title_year" in set(decisions["rule"])


def test_fuzzy_candidate_not_auto_without_author_overlap():
    cfg = load_config("configs/search_config.yaml")
    df = pd.DataFrame(
        [
            {"record_id": "a", "doi_normalized": None, "title_normalized": "quantum diffusion model", "year": 2024, "authors": "A", "retrieval_source": "Crossref", "database_scope": "IEEE"},
            {"record_id": "b", "doi_normalized": None, "title_normalized": "quantum diffusion models", "year": 2024, "authors": "B", "retrieval_source": "Crossref", "database_scope": "Springer"},
        ]
    )
    deduped, _, decisions = deduplicate_records(df, cfg)
    assert len(deduped) == 2
    assert "manual_review_candidate" in set(decisions["decision"])
