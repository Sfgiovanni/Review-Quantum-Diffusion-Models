"""Expected all-years selection flow against the committed screening data.

These counts describe the FROZEN corpus (the manual screening artifact over the
automated CORE + RELATED + MANUAL_REVIEW shortlist), not a live `update-search`,
which is expected to find new records and change the numbers.
"""

from pathlib import Path

import pytest

from quantum_diffusion_search.apply_screening import apply_screening

SCREENING = Path("data/screening/manual_screening.csv")
POOL = Path("data/processed/papers_core.csv")

pytestmark = pytest.mark.skipif(
    not (SCREENING.exists() and POOL.exists()),
    reason="committed screening data not present",
)


def test_committed_selection_flow(tmp_path):
    s = apply_screening(SCREENING, Path("data/processed"), tmp_path / "reports")
    assert s["core_unique_candidates"] == 72   # CORE 54 + MANUAL_REVIEW 17 + RELATED 1
    assert s["included"] == 48                  # CORE after manual screening
    assert s["related"] == 3
    assert s["pending"] == 3
    assert s["excluded"] == 18
    assert s["review_corpus"] == 48
    assert s["manually_added_beyond_pool"] == 0
