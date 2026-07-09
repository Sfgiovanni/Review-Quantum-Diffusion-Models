from quantum_diffusion_search.config import load_config


def test_smoke_config_does_not_write_processed_outputs():
    cfg = load_config("configs/search_config_smoke.yaml")
    assert cfg["run_mode"] == "smoke"
    assert cfg["directories"]["processed"].startswith("data/smoke/")
    assert cfg["directories"]["raw"].startswith("data/smoke/")
