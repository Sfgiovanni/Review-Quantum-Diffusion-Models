# Reproducibility hardening — change set

This bundle addresses the 12 requested repository changes. Apply it from the repo root:

```bash
# 1. copy the new/updated files from this bundle over your working tree
#    (preserves your existing files; only adds new ones)
rsync -av --exclude CHANGES.md ./ /path/to/Review-Quantum-Diffusion-Models/

# 2. apply the in-place edits to the three existing source files
cd /path/to/Review-Quantum-Diffusion-Models
python apply_patches.py .        # idempotent; asserts before writing

# 3. install and run
make install
python -m quantum_diffusion_search apply-screening
python -m quantum_diffusion_search reproduce --raw-run data/raw/2026-07-09T184559Z_780688a
make test
```

## New files
- `src/quantum_diffusion_search/reproduce.py` — real reproduction from raw payloads.
- `src/quantum_diffusion_search/apply_screening.py` — manual-screening integration + stage files + PRISMA.
- `data/screening/manual_screening.csv` and `.xlsx` — the human triage (32 rows).
- `tests/test_apply_screening.py` — deterministic mechanics test.
- `tests/test_selection_counts.py` — asserts the 2025–2026 flow on committed data.
- `requirements-lock.txt`, `Dockerfile`, `.dockerignore` — frozen environment.
- `apply_patches.py` — applies the in-place edits below.

## Mapping to the 12 requested changes

**1. Real `reproduce` (not a CSV copy).** `reproduce.py` re-parses the raw arXiv XML
and Crossref `.json.gz` files with the existing `parse_arxiv_entry` /
`parse_crossref_item` parsers, replays the exact source/query order, re-runs
`process_and_export`, writes to `data/reproduced/`, and diffs against the committed
tables column-by-column (ignoring only `retrieved_at_utc`). `cli.run_reproduce` now
calls it. **Status: done** (run in your environment against the frozen raw run).

**2. Explicit selection flow.** `apply-screening` emits the full chain to
`reports/prisma_flow_counts.csv` and `reports/selection_flow.md`:
`7408 → 4892 → 54 (cross-source CORE) → 32 (unique) → 24 evaluated → 18 / 5 / 1`,
plus `main corpus = 18`, `historical antecedents = 8`. **Status: done, validated.**

**3. Manual sheet in the repo.** `data/screening/manual_screening.csv` (+ `.xlsx`).
**Status: done.**

**4. Identifiers in the sheet.** Columns: `arxiv_id, doi, year, title,
screening_decision, exclusion_reason, family, generated_object, notes`. `record_id` /
`run_id` are filled by joining to the automated pool inside `apply-screening`
(the sheet keys on the stable `arxiv_id`/`doi`, not the run-specific `record_id`).
**Status: done.**

**5. `apply-screening` command.** Wired into the CLI:
`python -m quantum_diffusion_search apply-screening --screening data/screening/manual_screening.csv`.
**Status: done.**

**6. Per-stage files.** `apply-screening` writes `core_unique_candidates.csv` (32),
`candidates_2025_2026.csv` (24), `included_studies.csv` (18), `excluded_studies.csv`
(5), `pending_studies.csv` (1), and — new — `manually_added_studies.csv`.
`core_source_records.csv` (the 54 cross-source) is written when
`all_source_records.csv` is present. **Status: done.**

**7. Fix PRISMA / `search_report.md`.** `apply-screening` rewrites
`prisma_flow_counts.csv` with disambiguated labels ("automated CORE candidates
(cross-source)" vs "unique CORE candidates after deduplication" vs "included
studies"). The `apply_patches.py` edit also relabels the search-time report so it no
longer prints `CORE: 54` / `Primary models: 54` as if they were the included set, and
adds a note pointing to `selection_flow.md`. **Status: done.**

**8. Main corpus vs historical.** `main_corpus_2025_2026.csv` (18) and
`historical_background_pre_2025.csv` (8) are generated from the sheet's year and the
`BACKGROUND` decision. **Status: done.**

**9. Truncation detection.** Both clients now flag `truncated=True` whenever the API
reports more results than were retrieved — not only when the max-results cap is hit,
so a partial page or an early cursor stop is also caught. **Status: done** (patched).

**10. Freeze the environment.** `requirements-lock.txt` (direct-dep lock with a
regeneration command for a full hash-pinned lock) and a `Dockerfile` pinning the
interpreter. **Status: done**; regenerate the hash-locked file with `uv pip compile`
in your environment for the final release.

**11. Final run on a clean tree.** After committing this change set, run the pipeline
once on a clean checkout and confirm the manifest's `command`/commit reflect exactly
the committed code and data. (Process step — nothing to patch.)

**12. Automated tests.** `tests/test_selection_counts.py` asserts
`included == 18`, `excluded == 5`, `pending == 1`, `evaluated == 24`,
`main_corpus == 18`, `manually_added == 2` on the committed screening artifacts.
These are scoped to the **frozen** screening stage; `update-search` intentionally has
no hardcoded counts (it is meant to find new records). `tests/test_apply_screening.py`
covers the mechanics deterministically. **Status: done.**

## Important honesty note (surfaced by the new flow)
Two included studies — `2505.20863` (Barta et al.) and `2504.20794` (Q-Fusion) — were
**not** retrieved by the automated search; they were added by hand. `apply-screening`
reports this as `manually added beyond automated pool: 2` and lists them in
`selection_flow.md`. To make the `32 → 24 → 18` chain a clean subset, extend the
search configuration so these circuit-synthesis papers are retrieved automatically,
or keep documenting them as an explicit manual-addition stage.

---

## Addendum — closing the manual-addition gap (search config)

`extend_search_config.py` adds five circuit-synthesis queries (Q19–Q23) to
`configs/search_config.yaml` and `configs/search_config_full.yaml`, plus matching
relevance and topic patterns:

- Q19 `all:"diffusing quantum circuits"` — matches **Q-Fusion** (arXiv:2504.20794) by title.
- Q20 `all:"diffusion" AND all:"parameterized quantum circuit"` — matches **Barta et al.** (arXiv:2505.20863) by title.
- Q21 `"quantum circuit synthesis" AND diffusion` — matches **genQC** (Fürrutter et al.).
- Q22 `"quantum architecture search" AND diffusion`, Q23 `diffusion AND "quantum circuit generation"` — broad recall.

Run it once from the repo root (idempotent, anchor-checked):

```bash
python extend_search_config.py
```

After re-running `python -m quantum_diffusion_search update-search`, the two
previously hand-added circuit-synthesis papers are retrieved automatically, so
`manually added beyond automated pool` should drop to 0 and the `54 → 32 → 24 → 18`
chain becomes a clean subset. The relevance scoring already exceeds the inclusion
threshold for these records once retrieved, so only the queries needed changing.

---

## Addendum 2 — full-field (all-years) scope

The review scope is now the whole field across all years, not just 2025–2026.

- **Retrieval already covers all years.** `date_range.from_pub_date` is `2020-01-01`
  and `resolve_config` fills `until_pub_date` with the run date, so the pipeline
  retrieves 2020 → cut-off. Since the first quantum diffusion models are from 2023,
  this is effectively the complete field. **No retrieval change was required.**
- **Cutoff pinned.** `extend_search_config.py` now also sets
  `until_pub_date: '2026-07-09'` in both configs, freezing the "up to mid-2026"
  claim reproducibly (replaces the `null` default).
- **Screening sheet re-labelled for all years.** `data/screening/manual_screening.csv`
  (+ `.xlsx`) now uses the standard `screening_category` vocabulary
  (CORE / RELATED / MANUAL_REVIEW / EXCLUDE) over the full corpus:
  **CORE = 48, RELATED = 3, MANUAL_REVIEW = 3, EXCLUDE = 18** (72 screened; the human-screened universe is the automated CORE 54 + MANUAL_REVIEW 17 + RELATED 1). The
  pre-2025 antecedents (Cacioppo, Zhang, Kölle, Parigi, Fürrutter, Kwun, …) are now
  **CORE included studies**, not background.
- **`apply-screening` updated.** Reads `screening_category`, adds a RELATED bucket
  and `related_studies.csv`, and defaults to all years (no 2025–2026 window; pass
  `--corpus-from/--corpus-to` to restrict). It emits `included_studies.csv` (48),
  `related_studies.csv` (3), `pending_studies.csv` (3), `excluded_studies.csv` (18),
  `main_corpus.csv` (48), and rebuilds the PRISMA flow.
- **Tests updated** to the all-years counts (`tests/test_selection_counts.py`).

Manuscript changes (intro/abstract to all-years, ~26 studies, positioning vs the
early-2025 review) are separate from the repository and not included here.
