import pandas as pd

from quantum_diffusion_search.legacy import reconcile_legacy


def test_all_legacy_filtered_records_are_reconciled(tmp_path):
    legacy = pd.DataFrame([
        {"title": "Quantum diffusion model", "arxiv_id_base": "2501.00001", "doi": None, "year": 2025},
        {"title": "Quantum DDPM", "arxiv_id_base": "2501.00002", "doi": "10.1109/x", "year": 2025},
    ])
    unique = pd.DataFrame([
        {"record_id": "R1", "title": "Quantum diffusion model", "title_normalized": "quantum diffusion model", "arxiv_id": "2501.00001", "doi_normalized": None, "authors": "A", "arxiv_source": True, "ieee_crossref_source": False, "springer_crossref_source": False},
        {"record_id": "R2", "title": "Quantum DDPM", "title_normalized": "quantum ddpm", "arxiv_id": None, "doi_normalized": "10.1109/x", "authors": "B", "arxiv_source": False, "ieee_crossref_source": True, "springer_crossref_source": False},
    ])
    reconciled = reconcile_legacy(legacy, unique, tmp_path / "legacy.csv")
    assert len(legacy) == len(reconciled)
    assert (reconciled["final_status"] == "matched").all()
