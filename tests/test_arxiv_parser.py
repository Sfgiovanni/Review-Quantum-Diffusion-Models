from types import SimpleNamespace

from quantum_diffusion_search.clients.arxiv_client import parse_arxiv_entry


def test_parse_arxiv_entry():
    entry = SimpleNamespace(
        id="http://arxiv.org/abs/2506.19270v1",
        title="Quantum Diffusion Model",
        summary="A denoising diffusion model.",
        authors=[SimpleNamespace(name="Ada Lovelace")],
        published="2025-06-10T00:00:00Z",
        updated="2025-06-11T00:00:00Z",
        tags=[{"term": "quant-ph"}],
        links=[{"type": "application/pdf", "href": "https://arxiv.org/pdf/2506.19270"}],
        link="https://arxiv.org/abs/2506.19270",
        arxiv_doi="10.1234/example",
        arxiv_journal_ref="Journal",
    )
    row = parse_arxiv_entry(entry, query_id="Q01", query_text='all:"quantum diffusion model"', run_id="run", raw_source_file="raw.xml")
    assert row["arxiv_id"] == "2506.19270"
    assert row["year"] == 2025
    assert row["authors"] == "Ada Lovelace"
