from quantum_diffusion_search.normalization import (
    clean_text,
    extract_arxiv_id,
    extract_year,
    normalize_doi,
    normalize_title,
    parse_crossref_date,
)


def test_normalize_doi_removes_url_and_noise():
    assert normalize_doi(" https://doi.org/10.1109/ABC.2024.1. ") == "10.1109/abc.2024.1"


def test_normalize_doi_rejects_non_doi():
    assert normalize_doi("not a doi") is None


def test_normalize_title_unicode_and_punctuation():
    assert normalize_title(" Quantum\nDiffusion: Schrödinger Models! ") == "quantum diffusion schrodinger models"


def test_clean_text_preserves_original_words():
    assert clean_text("a\n  b") == "a b"


def test_extract_year():
    assert extract_year("2025-06-10T00:00:00Z") == 2025


def test_extract_arxiv_id_without_version():
    assert extract_arxiv_id("https://arxiv.org/abs/2506.19270v2") == "2506.19270"


def test_parse_incomplete_crossref_date():
    assert parse_crossref_date({"date-parts": [[2024]]}) == "2024-01-01"
