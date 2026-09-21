# Codebook — Quantum Diffusion Models systematic review

**Version:** 2.0-draft · **Status:** proposal, not yet applied to the corpus
**Companion files:** `codebook_schema.yaml` (machine-readable field list),
`evidence_indicators.csv` (three evaluation fields already coded)

This document defines every field extracted from the included studies: what it
means, which values it may take, and how to decide borderline cases. Two coders
following it independently should produce the same row for the same study.

> **Why version 2.0.** Version 1 was implicit — the rules lived in the coders'
> heads and in scattered notes. Section 3.3 of the manuscript states that a
> complete codebook is available with the review artifacts, so this file closes
> that gap. It also resolves the ambiguities raised in review: qubit counts that
> mix different roles, an undefined notion of "training on hardware", `NR`
> conflated with `NA`, and a taxonomy whose decision flow does not always
> reproduce the recorded class.
>
> **Applying v2.0 requires recoding all synthesis units.** Some values, and
> therefore some counts, may change. Do not mix v1 and v2 rows.

---

## 1. Scope and unit of analysis

### 1.1 Synthesis unit

The unit of extraction and of every reported count is the **synthesis unit**: one
study, not one bibliographic record.

Reports are consolidated into a single synthesis unit when they describe the same
underlying study, or when a later report is a cumulative version reusing the
central mechanism and evidence of an earlier one. Substantively independent
extensions stay separate.

When a synthesis unit has several reports:

- **Mechanism and classification fields** may draw on all linked reports.
- **Experimental fields** (`qubits_*`, `device`, `hardware_stage`, `shots`,
  `depth`, evaluation fields) are taken from the report that actually performed
  the experiment, and `*_source` records which one.
- **Chronology** uses the earliest included public disclosure.

Every linkage decision is recorded in `linkage_log.csv` with the reason.
Consolidation is a synthesis-level judgement and never implies that the records
are bibliographically identical.

### 1.2 Evidence requirement

Every coded field has a companion `<field>_source` holding a locator in the
primary source — section number, figure, table, or page — and, where short, the
verbatim sentence supporting the code.

- Values are **never** inferred from software frameworks, architectural
  conventions, or what implementations of this kind usually do.
- If the locator cannot be written, the field is `NR`, not a guess.
- Coder judgement that goes beyond the quoted text belongs in `notes`, never in
  the coded value.

### 1.3 Procedure

Two coders extract independently. Disagreements are resolved by discussion, and
by a third coder when discussion does not settle them. Agreement is computed on
the double-coded subset and reported in the manuscript with the statistic used,
the number of units, and the fields covered.

---

## 2. Universal value conventions

These apply to every field unless its own entry says otherwise.

| Code | Meaning |
|---|---|
| `NR` | The indicator applies to this study, but the source does not report it, or reports it too vaguely to code. |
| `NA` | The indicator does not conceptually apply to this study design. |

**`NR` vs `NA` — decision rule.** Ask: *could this study have reported the field?*

- Yes, but it did not → `NR`
- No, the field is meaningless for this design → `NA`

Worked cases:

- A purely theoretical contribution has no seeds to report → `multiple_runs = NA`.
- A continuous-variable model has no qubit count → `qubits_* = NA`.
- An implemented model whose paper never states the circuit width → `NR`.
- A classical diffusion model that generates circuits has no generator qubits
  (`qubits_generator_* = NA`) but does have `qubits_target_circuit`.

Never write a combined `NR/NA`. Every cell resolves to exactly one of them.

---

## 3. Identity and chronology

| Field | Values | Definition |
|---|---|---|
| `unit_id` | string | Stable identifier of the synthesis unit (BibTeX key of the primary report). |
| `reports` | list of strings | All bibliographic records consolidated into this unit. |
| `title`, `authors` | string | Of the primary report. |
| `first_disclosure_year` | integer | Year of the earliest included public disclosure of the unit. |
| `venue_name` | string | Journal or conference **name**, never the publisher. "Quantum Machine Intelligence", not "Springer Nature". |
| `venue_type` | `journal` \| `conference` \| `conference proceedings` \| `preprint` | |
| `peer_reviewed` | `yes` \| `no` | `no` for preprint-only units at the search cut-off. |

---

## 4. Operational classification

### 4.1 `primary_class` — **goes in the paper**

One class per unit, by **dominant operational contribution**: the component
around which the study's main methodological novelty and evaluation are
organised.

| Value | Definition |
|---|---|
| `quantum_native` | Perturbation or recovery acts directly on quantum states, channels, trajectories, measurement distributions, or continuous-variable systems. |
| `hybrid_denoiser` | A quantum circuit performs a central denoising, conditioning, feature, or correction operation inside a predominantly classical-data diffusion pipeline. |
| `quantum_latent` | A quantum module is central to diffusion or generation inside a learned compressed representation. |
| `quantum_noise_driven` | Physical quantum noise or hardware randomness is an active generative resource, not merely an implementation error. |
| `circuit_param_synthesis` | A predominantly classical diffusion model generates quantum circuits, gate sequences, ansatzes, or variational parameters. |
| `theory_foundations` | Establishes feasibility conditions or fundamental limitations without a sufficiently specific operational configuration for the classes above. |

### 4.2 Precedence rules — **go in the paper**

Several studies satisfy more than one definition. Apply the rules **in order**
and stop at the first that fires. This ordering is what makes the class
reproducible from the decision flow.

> **R1 — Generated object outranks diffusion space.**
> If the main contribution is generating quantum circuits, gate sequences,
> ansatzes, or variational parameters, and the diffusion process itself is
> predominantly classical → `circuit_param_synthesis`.
> *Rationale: the quantum element is the output, not the computational engine.*

> **R2 — Physical noise as a resource outranks everything below.**
> If device noise or hardware randomness supplies the generative mechanism
> (rather than degrading it) → `quantum_noise_driven`.

> **R3 — Learned compression outranks the diffusion space.**
> If diffusion or generation happens inside a learned compressed representation
> and that representation is central to the contribution and its evaluation →
> `quantum_latent`, **even when the objects diffused are quantum states**.
> *This rule is why a quantum-state generator built on a learned latent space is
> classified as `quantum_latent` and not `quantum_native`.*

> **R4 — Diffusion space.**
> If perturbation or recovery acts directly on states, channels, trajectories,
> measurement distributions, or CV systems → `quantum_native`.

> **R5 — Function of the quantum element.**
> If a PQC performs denoising, conditioning, feature extraction, or correction
> inside a classical-data pipeline → `hybrid_denoiser`.

> **R6 — Residual.**
> Otherwise → `theory_foundations`.

**Validation requirement.** After coding, a second person re-derives
`primary_class` for every unit from these rules alone, without seeing the
recorded value. Disagreements are either coder error or a gap in the rules; a gap
is fixed here, in the codebook, and the whole corpus is re-derived. The
manuscript reports how many units were re-derived and how many matched.

**Note on Figure 2.** The published decision flow asks about the diffusion space
first, which sends every study diffusing over quantum states to
`quantum_native` and therefore cannot reproduce a `quantum_latent`
state-generation unit. Adopting R1–R6 means redrawing Figure 2 in this order.

### 4.3 Secondary descriptors

`secondary_descriptors` is multi-label and never changes `primary_class`.
Allowed: `conditional`, `score_based`, `latent`, `measurement_based`,
`open_system`, `continuous_variable`, `hardware_oriented`, `theoretical`.

---

## 5. Generative objective — **goes in the paper**

`generative_objective` separates aims that are not comparable to each other and
must not be pooled into a single performance narrative.

| Value | Definition | Typical evaluation |
|---|---|---|
| `state_generation` | Produce quantum states matching a target state or family. | Fidelity, trace distance |
| `distribution_learning` | Learn a distribution over states or over classical data and sample from it. | MMD, Wasserstein, FID, KID |
| `state_restoration` | Recover a state that was corrupted by a known or learned noise process. | Fidelity against the pre-corruption state |
| `classical_data_generation` | Produce classical data (images, time series, features). | FID, IS, SSIM, task metrics |
| `circuit_synthesis` | Produce circuits, gate sequences, ansatzes, or parameters. | Validity, novelty, resources, task performance |
| `theoretical` | No generated artifact. | `NA` |

**Rule.** Restoring a corrupted state is *not* evidence of state generation, and
generating one state is *not* evidence of having learned a distribution. When a
study addresses more than one, `generative_objective` records the one its
headline claim rests on, and the others go in `secondary_objectives`.

Cross-study comparison is only reported within a shared
(`generative_objective`, dataset or target family) pair.

---

## 6. Experimental scale — qubit fields

### 6.1 Why the split — **goes in the paper**

A single "qubits" column mixes quantities that mean different things: the width
of the generative circuit, its ancillas, the width of a circuit the model
*produced*, and the width of a downstream task used only for evaluation. Summed
together they overstate the demonstrated scale. Each role gets its own field, and
only one of them feeds the scale synthesis.

| Field | Counts | Excludes |
|---|---|---|
| `qubits_generator_sim` | Widest circuit implementing the forward or reverse process, in classical simulation. | Ancillas; generated target circuits; downstream evaluation. |
| `qubits_generator_hw` | Same, executed on a physical device. | Idem. |
| `qubits_ancilla` | Ancillas used for readout, Hadamard tests, conditioning, or time embedding. | Data qubits. |
| `qubits_target_circuit` | Width of the circuit the model generates, for synthesis studies. | The generator, which is classical in these studies. |
| `qubits_downstream_eval` | Width of a circuit used only to evaluate a generated artifact on a later task. | Everything the generative model itself runs. |

**Which field feeds the scale figure:** `qubits_generator_sim` and
`qubits_generator_hw`, plotted as separate series. No other qubit field enters
the scale synthesis, and no qubit fields are ever summed.

### 6.2 Common rules

- Code only what is explicitly reported or unambiguously determined from the
  implemented experiment.
- When several sizes are evaluated, record the **maximum implemented** size in
  that execution context, and keep the full range in `qubits_range`.
- Continuous-variable models: `NA`, not `NR`.

### 6.3 `qubits_confirmed`

`yes` | `no`. `no` marks a value the source discusses as a scalability
projection without establishing that it was implemented. Unconfirmed values are
excluded from the quantitative scale synthesis and reported separately.

### 6.4 Interpretation guard

Fewer parameters, or more qubits, taken in isolation, demonstrate neither
efficiency nor quantum advantage. Resource claims are coded only when the source
states a like-for-like comparison, and the comparison's terms go in
`resource_claim_basis`.

---

## 7. Execution setting

### 7.1 `hardware_stage` — **goes in the paper**

Which stage of the pipeline ran on a physical device.

| Value | Definition |
|---|---|
| `none` | Everything in classical simulation, including noisy simulators and fake backends. |
| `forward_on_device` | The forward/corruption process ran on hardware; the reverse model was trained offline on the resulting data. |
| `training_in_loop` | Circuits were executed on the QPU during training, inside the optimisation loop. |
| `sampling` | Device used to draw samples from a trained model. |
| `inference` | Device used for forward passes at evaluation time. |
| `post_training` | Device used for a demonstration after training, not part of the training or the reported metric pipeline. |

Multi-label where a study does several. `NA` for theoretical work.

**A noisy simulator or a "fake" backend is `none`.** It models a device; it is
not one.

### 7.2 `training_locus` — **goes in the paper**

Where the optimisation of the model's parameters happened. This is the field that
supports any statement about training on hardware.

| Value | Definition |
|---|---|
| `classical_simulation` | All circuit evaluations during training were simulated. |
| `hybrid_in_loop` | A classical optimiser drove parameters while circuits ran on the QPU during training. **This counts as real hardware participation in training.** |
| `end_to_end_hardware` | The full training loop, including optimisation, executed on quantum hardware. |
| `not_trained` | Analytical or training-free method. |
| `NA` | Theoretical contribution. |

**Rule.** `hybrid_in_loop` is hardware training with a classical optimiser, and a
claim that no study trains on hardware must be stated against
`end_to_end_hardware`, not against `hybrid_in_loop`. Note also that
`forward_on_device` means hardware produced the training data, which is neither
of the two — say which one is meant.

### 7.3 Other execution fields

| Field | Values | Notes |
|---|---|---|
| `simulator` | string \| `NR` \| `NA` | Name and version where stated. Record the platform, not just "classical simulator". |
| `device` | string \| `NR` \| `NA` | Named backend. `NR` when a device is used but unnamed. |
| `noise_model` | string \| `none` \| `NR` | |
| `shots` | integer \| string \| `NR` \| `NA` | Record the quantity as reported and say what it counts (per circuit, per state, total) in `shots_basis`. Where the source is internally inconsistent, record the inconsistency in `notes` rather than picking one. |
| `depth` | string \| `NR` \| `NA` | In the architectural unit the source uses, stated in the value (e.g. "12 layers per reverse PQC"). Not standardised across studies. |
| `circuit_evaluations_per_sample` | integer \| `NR` \| `NA` | Number of circuit executions along the reverse trajectory, where derivable. |

---

## 8. Evaluation and comparison

### 8.1 `classical_baseline`

`yes` | `no` | `na`

`yes` requires an explicit comparison against a non-quantum comparator
addressing the **same task objective**. Random parameter initialisation, random
search, and randomly generated ansatzes count when used as explicit comparators.

- A mismatch in resource budget between the method and its comparator is a
  **limitation of the comparison**, recorded in `baseline_resource_match`, not a
  reason to code `no`.
- Comparison only against other quantum models is `no`.
- `na` only for units with no empirical evaluation.

### 8.2 `multiple_runs`

`yes` | `no` | `na`

`yes` requires explicitly documented multiple seeds or independent runs.

**Do not count as independent repetitions:** measurement shots; multiple samples
drawn from one trained model; folds derived from the same training procedure; a
single reported seed.

`na` only for units with no empirical execution.

### 8.3 `uncertainty_reported`

`yes` | `no` | `na`. Standard deviations, confidence intervals, box plots, or
comparable dispersion measures.

### 8.4 `metrics`

List of metric names **as reported**, mapped to normalised families in
`metric_families`. A metric used only as a training objective is flagged
`training_objective_only` so it is not read as a final evaluation measure.

Families: `image_quality`, `distributional_similarity`, `quantum_state_quality`,
`task_performance`, `circuit_quality`, `uncertainty`, `computational_resources`.

Recording that a metric was used is separate from judging it adequate for the
claim; adequacy commentary belongs in the synthesis, not in this field.

### 8.5 `input_interface`, `readout_strategy`

Coded from the families used in the manuscript figures. Multi-label. `NR` when a
measurement is described without identifying its basis; `NA` when the study has
no quantum model interface.

---

## 9. Reproducibility

| Field | Values | Rule |
|---|---|---|
| `public_code` | `yes` \| `no` \| `na` | `yes` only for code identified as publicly available at the search cut-off. An announced or planned release is `no`. |
| `code_url` | string \| `NR` | |
| `public_data` | `yes` \| `no` \| `na` | |

---

## 10. Which fields appear in the manuscript

The complete codebook lives in the repository. Four definitions carry the
manuscript's headline claims and must be visible to a reader who never leaves the
PDF:

1. **The qubit role split** (§6.1) — supports the reported scale range.
2. **`training_locus` and `hardware_stage`** (§7.1, §7.2) — support every
   statement about hardware execution and training.
3. **`NR` vs `NA`** (§2) — supports every denominator.
4. **The taxonomy precedence rules R1–R6** (§4.2) — support the class counts.

`generative_objective` (§5) is also reported, since it defines which comparisons
the synthesis is willing to make.

Suggested placement: Table 2 becomes a field-definition table covering these;
Appendix B carries the full field list; Section 3.3 points to this file for the
complete rules.

---

## 11. Change log

| Version | Change |
|---|---|
| 2.0-draft | First written codebook. Splits qubit roles; defines `training_locus` and `hardware_stage`; separates `NR` from `NA`; adds ordered taxonomy precedence rules R1–R6; adds `generative_objective`; requires `*_source` locators on every coded field. |

---

## 12. Open decisions

Confirm these before recoding:

1. **R3 before R4.** Placing learned-latent ahead of diffusion space is what makes
   a latent quantum-state generator reproducible from the flow. It may move
   units between `quantum_native` and `quantum_latent` and change the class
   counts. Confirm the ordering, then recode.
2. **`forward_on_device` as its own stage.** The alternative is folding it into
   `training_in_loop`, which would overstate optimisation on hardware.
3. **Whether `secondary_objectives` is worth carrying** or whether one objective
   per unit is enough.
4. **Agreement statistic** to compute on the double-coded subset, and its size.
