# Manual screening — full field, all years (2020–2026)

`manual_screening.csv` (and the formatted `manual_screening.xlsx`) is the human
screening artifact for the **all-years** review corpus. The review no longer
restricts itself to 2025–2026: it covers the field from its emergence (first
quantum diffusion models appear in 2023) through the July 2026 search cut-off, and
supersedes the early-2025 narrative overview with a systematic, reproducible
protocol.

## Columns
- `arxiv_id`, `doi` — stable identifiers used to join to the automated pool.
- `year`, `title` — study metadata.
- `screening_category` — one of:
  - **CORE** — a primary quantum diffusion model study, included in the review corpus.
  - **RELATED** — supporting work (e.g. an evaluation metric), cited but not a primary study.
  - **MANUAL_REVIEW** — pending a full-text decision.
  - **EXCLUDE** — off-topic (e.g. nuclear-physics "color transparency", where "quantum diffusion" denotes transport, not a generative model).
- `exclusion_reason` — required for EXCLUDE.
- `family`, `generated_object` — taxonomy attributes.
- `notes` — free text.

## Counts (frozen)
Built from the automated shortlist: CORE (54) + MANUAL_REVIEW (17) + RELATED (1) = 72 records, human-screened.

| Screening category | Count |
|---|---|
| CORE (review corpus) | 48 |
| RELATED | 3 |
| MANUAL_REVIEW (pending full-text) | 3 |
| EXCLUDE | 18 |
| **Total screened** | **72** |

Each row also carries `automated_category` (the pipeline's CORE/RELATED/MANUAL_REVIEW
label) and a `confidence` flag (high/medium) on the manual decision.

## Regenerate the flow
```bash
python -m quantum_diffusion_search apply-screening \
  --screening data/screening/manual_screening.csv
```
This writes the per-stage tables to `data/processed/` (`included_studies.csv`,
`related_studies.csv`, `pending_studies.csv`, `excluded_studies.csv`,
`main_corpus.csv`, `manually_added_studies.csv`) and rebuilds
`reports/prisma_flow_counts.csv` + `reports/selection_flow.md`.
