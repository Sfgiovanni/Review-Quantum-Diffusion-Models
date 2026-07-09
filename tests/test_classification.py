from quantum_diffusion_search.classification import classify_record
from quantum_diffusion_search.config import load_config


def test_multilabel_classification():
    cfg = load_config("configs/search_config.yaml")
    record = {"title": "Quantum circuit DDPM", "abstract": "denoising diffusion with a quantum circuit"}
    labels = classify_record(record, cfg["topic_patterns"])
    assert "DDPM / denoising diffusion" in labels
    assert "quantum circuit diffusion" in labels


def test_other_classification():
    cfg = load_config("configs/search_config.yaml")
    assert classify_record({"title": "Unrelated", "abstract": ""}, cfg["topic_patterns"]) == "other / manual assessment required"
