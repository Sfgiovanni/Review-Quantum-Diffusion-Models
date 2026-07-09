# Original Notebook Assessment

## Summary

The original notebook performs an arXiv-only search for quantum diffusion model literature. It installs missing packages inside the notebook, defines 18 arXiv queries, retrieves results from the public arXiv API, parses metadata into a pandas table, deduplicates by arXiv ID without version suffix, applies a minimum year filter, computes a heuristic relevance score, assigns a single topic label, and exports CSV, XLSX, and Markdown bibliography files.

## Queries and Parameters

The notebook uses exact and conjunctive arXiv queries covering quantum diffusion models, denoising diffusion, score-based models, stochastic Schrödinger diffusion, quantum generative models, quantum circuits, quantum neural networks, variational quantum models, DDPM, score matching, and Schrödinger bridges.

Parameters were:

- `BATCH_SIZE = 100`
- `SLEEP_SECONDS = 3.0`
- `MAX_RESULTS_PER_QUERY = 300`
- `MIN_YEAR = 2020`
- `MIN_RELEVANCE_SCORE = 6`
- `SORT_MODE = published_desc`

## Helper Functions

The notebook defines helpers for whitespace normalization, arXiv version stripping, year extraction, safe filenames, arXiv entry parsing, relevance scoring, topic classification, arXiv pagination, internal search, short author formatting, Markdown bibliography generation, and optional PDF download.

## Table Schema

The arXiv table includes query, arXiv ID, versionless arXiv ID, title, authors, published and updated dates, year, primary category, categories, summary, comment, journal reference, DOI, abstract URL, PDF URL, relevance score, and topic class.

## Relevance Score

The score adds base points for `quantum` and `diffusion`, adds weighted positive regex matches for diffusion/generative/QML terms, and subtracts weighted negative matches for likely physical diffusion topics. This was preserved but moved to configuration and extended to return score explanations and matched patterns.

## Topic Classification

The original classification was mutually exclusive and returned the first matching class. It covered DDPM, score-based diffusion, stochastic Schrödinger diffusion, Schrödinger bridge, quantum circuit/QNN generative models, quantum generative models, and other/manual check. The refactor preserves these concepts but supports multi-label classification.

## Deduplication

The notebook deduplicates only by versionless arXiv ID. The refactor preserves arXiv ID normalization and adds DOI, publication/preprint linkage, exact normalized title/year, and conservative fuzzy candidate detection while retaining provenance.

## Exports

The original notebook exports:

- `arxiv_quantum_diffusion_all.csv`
- `arxiv_quantum_diffusion_all.xlsx`
- `arxiv_quantum_diffusion_filtered.csv`
- `arxiv_quantum_diffusion_filtered.xlsx`
- `arxiv_quantum_diffusion_bibliography.md`
- optional PDFs

## Strengths

- Uses the public arXiv API without API keys.
- Uses multiple smaller queries rather than one fragile query.
- Respects a delay between arXiv requests.
- Provides transparent heuristic scoring.
- Exports inspectable CSV/XLSX files.

## Limitations

- arXiv only; no IEEE or Springer scope.
- Scientific parameters are embedded in notebook cells.
- Notebook installs dependencies at runtime.
- No tests, CLI, manifest, raw-response preservation, or stable run provenance.
- Deduplication is limited to arXiv IDs.
- Topic classification is mutually exclusive.
- Errors can be printed and ignored at query level.
- Optional PDF download is present in the notebook workflow.

## Refactoring Decisions

The refactor moves search decisions to `configs/search_config.yaml`, implements a package under `src/`, preserves the arXiv query concepts and scoring patterns, adds Crossref clients for DOI-prefix scoped IEEE and Springer metadata, stores raw responses, generates manifests and checksums, produces screening templates and reports, and adds offline tests.

## Preserved Components

- All original arXiv query concepts.
- Pagination and request delay behavior.
- Versionless arXiv IDs.
- Metadata fields for title, authors, abstract, categories, dates, journal reference, DOI, abstract URL, and PDF URL.
- Positive and negative relevance scoring logic, with more conservative negative weights.
- Core topic classes.

## Changed Components

- Query definitions are versioned and source-specific in YAML.
- Scoring is explainable and configurable.
- Classification is multi-label.
- Deduplication preserves provenance across arXiv and Crossref.
- Outputs follow a unified documented schema.
- Notebook logic is replaced by package imports and analysis cells.
- PDF download is not part of the default pipeline.
