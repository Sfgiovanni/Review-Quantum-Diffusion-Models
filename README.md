# Quantum Diffusion Literature Search

This repository provides a reproducible literature-search pipeline for a review on **Quantum Diffusion Models**.

IEEE- and Springer-scoped records are retrieved from the Crossref REST API using DOI-prefix restrictions. The repository does not claim direct programmatic access to IEEE Xplore or Springer Nature proprietary APIs.

## Scope

The pipeline searches:

- arXiv via the public arXiv API.
- IEEE-scoped Crossref metadata using DOI prefix `10.1109`.
- Springer-scoped Crossref metadata using DOI prefix `10.1007`.

No protected PDFs are downloaded by default and no API keys are required. `CROSSREF_MAILTO` is optional and enables Crossref polite-pool identification.

## Architecture

Scientific search decisions are centralized in `configs/search_config.yaml`. The notebook is only an analysis interface; acquisition, normalization, scoring, classification, deduplication, exporting, provenance, and reporting live in `src/quantum_diffusion_search/`.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
make install
```

Optional Crossref polite-pool configuration:

```bash
cp .env.example .env
export CROSSREF_MAILTO="your-email@example.org"
```

## Quick Run

```bash
python -m quantum_diffusion_search all --config configs/search_config.yaml
```

Small online smoke test:

```bash
make smoke-test
```

## Exact Reproduction

Exact reproduction uses frozen raw responses from an existing run and does not query external APIs:

```bash
python -m quantum_diffusion_search reproduce --raw-run data/raw/<run_id>
```

## Updating Searches

An updated search queries external APIs again and may retrieve different records due to new articles, metadata corrections, or API/index changes:

```bash
python -m quantum_diffusion_search update-search --config configs/search_config.yaml
```

## Outputs

Main outputs are written to:

- `data/processed/all_source_records.csv`
- `data/processed/all_source_records.parquet`
- `data/processed/deduplicated_records.csv`
- `data/processed/deduplicated_records.parquet`
- `data/processed/relevant_candidates.csv`
- `data/processed/relevant_candidates.xlsx`
- `data/processed/screening_template.xlsx`
- `reports/search_report.md`
- `reports/methods_text.md`
- `reports/prisma_flow_counts.csv`
- `data/raw/<run_id>/run_manifest.json`

## Search Strategy

Queries are versioned in `configs/search_config.yaml` and include stable `query_id`, conceptual text, arXiv syntax, Crossref syntax, rationale, and high-precision/high-recall labels. Exact request parameters and raw responses are preserved for every run.

## Deduplication

Deduplication is layered: DOI, arXiv/preprint-publication linkage evidence, exact normalized title and year, and conservative fuzzy title candidates. Fuzzy matches are not removed automatically without author/year evidence. Source provenance is preserved in duplicate groups and decisions files.

## Screening

`data/processed/screening_template.xlsx` is generated for human review. Automated relevance scoring is only a prioritization aid and must not be treated as an inclusion decision.

## Limitations

Crossref may lack abstracts, author details, or full publisher indexing. DOI-prefix scoping is transparent and reproducible but is not equivalent to direct IEEE Xplore or Springer Nature API access. Final inclusion requires human screening.

## Tests

```bash
make test
make lint
python scripts/execute_notebook.py
```

## Citation

Use `CITATION.cff`. After creating a GitHub release and archiving it on Zenodo, replace the placeholder DOI with the assigned Zenodo DOI.

## License

Code is MIT licensed. External metadata and linked content remain subject to the terms of their original providers.

## Zenodo Release

1. Push the repository to GitHub.
2. Connect the GitHub repository in Zenodo.
3. Create a semantic-versioned GitHub release, for example `v0.1.0`.
4. Let Zenodo archive the release.
5. Update `CITATION.cff` and `.zenodo.json` with the assigned DOI in a follow-up release.
