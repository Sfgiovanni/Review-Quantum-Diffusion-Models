# Reproducibility

## Exact Reproduction

Exact reproduction uses frozen raw files under `data/raw/<run_id>/` and does not perform new API calls. It is intended to reproduce normalization, deduplication, scoring, classification, tables, and reports from archived raw responses.

```bash
python -m quantum_diffusion_search reproduce --raw-run data/raw/<run_id>
```

## Search Update

An updated search queries arXiv and Crossref again:

```bash
python -m quantum_diffusion_search update-search --config configs/search_config.yaml
```

Updated searches can differ because new articles are published, metadata are corrected, APIs change, or indexes are updated.
