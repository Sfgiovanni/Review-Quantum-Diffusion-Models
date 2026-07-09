from quantum_diffusion_search.clients.crossref_client import parse_crossref_item


def test_parse_crossref_missing_abstract_and_authors():
    item = {
        "DOI": "10.1109/TEST.2024.1",
        "title": ["Quantum diffusion model"],
        "publisher": "IEEE",
        "container-title": ["Conference"],
        "type": "proceedings-article",
        "issued": {"date-parts": [[2024, 5]]},
        "URL": "https://doi.org/10.1109/TEST.2024.1",
    }
    row = parse_crossref_item(
        item,
        query_id="Q01",
        query_text='"quantum diffusion model"',
        run_id="run",
        database_scope="IEEE",
        retrieval_method="Crossref DOI-prefix search",
        doi_prefix="10.1109",
        raw_source_file="raw.json.gz",
    )
    assert row["abstract"] is None
    assert row["authors"] is None
    assert row["doi_normalized"] == "10.1109/test.2024.1"
    assert row["publisher_validation"] == "valid"


def test_parse_crossref_incomplete_date():
    item = {"DOI": "10.1007/x", "title": ["T"], "issued": {"date-parts": [[2023]]}}
    row = parse_crossref_item(
        item,
        query_id="Q",
        query_text="T",
        run_id="run",
        database_scope="Springer",
        retrieval_method="Crossref DOI-prefix search",
        doi_prefix="10.1007",
        raw_source_file="raw.json.gz",
    )
    assert row["publication_date"] == "2023-01-01"
