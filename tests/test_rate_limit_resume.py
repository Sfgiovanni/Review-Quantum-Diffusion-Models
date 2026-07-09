from pathlib import Path

import responses

from quantum_diffusion_search.clients.crossref_client import CrossrefClient
from quantum_diffusion_search.config import load_config, resolve_config


@responses.activate
def test_crossref_rate_limit_retry(tmp_path: Path):
    cfg = resolve_config(load_config("configs/search_config.yaml"))
    cfg["api"]["sleep_seconds"] = 0
    cfg["api"]["backoff"]["initial_seconds"] = 0
    cfg["api"]["max_attempts"] = 2
    client = CrossrefClient(cfg, tmp_path)
    url = "https://api.crossref.org/prefixes/10.1109/works"
    responses.add(responses.GET, url, status=429, headers={"Retry-After": "0"})
    responses.add(
        responses.GET,
        url,
        json={"status": "ok", "message": {"total-results": 0, "items": [], "next-cursor": "x"}},
        status=200,
    )
    rows, meta = client.fetch_query(cfg["queries"][0], "run", "IEEE", "Crossref DOI-prefix search", "10.1109")
    assert rows == []
    assert meta["api_total_results"] == 0
    assert client.retries == 1


def test_crossref_resume_from_cache(tmp_path: Path):
    cfg = resolve_config(load_config("configs/search_config.yaml"))
    cfg["api"]["sleep_seconds"] = 0
    client = CrossrefClient(cfg, tmp_path)
    import gzip
    import json

    raw = tmp_path / "Q01_10_1109_page0.json.gz"
    with gzip.open(raw, "wt", encoding="utf-8") as f:
        json.dump({"status": "ok", "message": {"total-results": 0, "items": [], "next-cursor": "x"}}, f)
    rows, _ = client.fetch_query(cfg["queries"][0], "run", "IEEE", "Crossref DOI-prefix search", "10.1109")
    assert rows == []
    assert client.http_requests == 0
