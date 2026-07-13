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

Two different things share the same category names, so keep them apart:

**Input — automated pipeline labels** (`automated_category` column). This is the
shortlist handed to the human reviewers, i.e. every record the pipeline did *not*
auto-exclude:

| Automated label | Count |
|---|---|
| CORE | 54 |
| MANUAL_REVIEW | 17 |
| RELATED | 1 |
| **Total handed to human screening** | **72** |

**Output — final human decision** (`screening_category` column). After full-text
review the 72 records are *re-distributed*: several automated "CORE" records were
physics false positives (e.g. color transparency) and became EXCLUDE, while several
automated "MANUAL_REVIEW" records (e.g. the Zhang QuDDPM and De Falco quantum latent
diffusion papers) were promoted to CORE:

| Final decision | Count |
|---|---|
| CORE (review corpus) | 48 |
| RELATED | 3 |
| MANUAL_REVIEW (pending full-text) | 3 |
| EXCLUDE | 18 |
| **Total screened** | **72** |

So the totals match (72 in, 72 out); only the per-category split changes between the
automated label and the human decision. Each row also carries a `confidence` flag
(high/medium) on the manual decision.

## Regenerate the flow
```bash
python -m quantum_diffusion_search apply-screening \
  --screening data/screening/manual_screening.csv
```
This writes the per-stage tables to `data/processed/` (`included_studies.csv`,
`related_studies.csv`, `pending_studies.csv`, `excluded_studies.csv`,
`main_corpus.csv`, `manually_added_studies.csv`) and rebuilds
`reports/prisma_flow_counts.csv` + `reports/selection_flow.md`.
