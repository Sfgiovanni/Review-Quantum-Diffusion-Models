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

**Output — final human decision** (`screening_category` column), after a manual
audit (2026-07-13). Several automated "CORE" records were physics false positives
(e.g. color transparency) and became EXCLUDE; several automated "MANUAL_REVIEW"
records (e.g. the Zhang QuDDPM and De Falco quantum latent diffusion papers) were
promoted to CORE; and a further 10 records that had passed an earlier screening pass
were reclassified to EXCLUDE on closer inspection as i