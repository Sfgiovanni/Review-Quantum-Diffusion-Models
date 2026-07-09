from quantum_diffusion_search.config import load_config
from quantum_diffusion_search.relevance import score_record


def test_scoring_returns_explanation():
    cfg = load_config("configs/search_config.yaml")
    record = {"title": "Quantum denoising diffusion probabilistic model", "abstract": "A quantum generative model with DDPM training."}
    result = score_record(record, cfg["relevance"])
    assert result["relevance_score"] >= 6
    assert "score=" in result["score_explanation"]
    assert result["positive_matches"]


def test_negative_patterns_do_not_exclude_by_themselves():
    cfg = load_config("configs/search_config.yaml")
    record = {"title": "Quantum spin diffusion", "abstract": "physical diffusion"}
    result = score_record(record, cfg["relevance"])
    assert result["negative_matches"]
    assert result["relevance_score"] >= 0
