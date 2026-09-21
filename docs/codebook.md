# Codebook — Quantum Diffusion Models systematic review

**Version:** 2.2 · **Status:** complete; awaiting application to the corpus
**Companion files:** `codebook_schema.yaml` (machine-readable field list),
`data/processed/evidence_indicators.csv` (three evaluation fields, coded),
`configs/screening_reasons.yaml` (exclusion reasons used during screening)

This document defines every field extracted from the included studies: what it
means, which values it may take, and how to decide borderline cases. Two coders
following it independently should produce the same row for the same study.

> **Scope.** This codebook governs **extraction** from studies that already
> passed screening. Search and screening are governed separately: the eligibility
> criteria are stated in the manuscript, and the exclusion-reason vocabulary is
> in `configs/screening_reasons.yaml`.
>
> **Applying v2.2 requires recoding all synthesis units.** Some values, and
> therefore some reported counts, will change — see §14. Do not mix rows coded
> under earlier rules with rows coded under this version.

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
- **Experimental fields** (`qubits_*`, `device`, `hardware_stage`,
  `training_locus`, `shots`, `depth`, evaluation fields) are taken from the
  report that performed the experiment, and `*_source` records which one.
- **Chronology** uses the earliest included public disclosure.

Consolidation is a synthesis-level judgement and never implies that the records
are bibliographically identical.

### 1.2 Linkage log

Every consolidation or separation decision is recorded, one row per decision, in
a linkage log published with the recoded extraction workbook as
`data/processed/linkage_log.csv`. Its format is specified here so that the log
and the workbook are produced together:

| Column | Content |
|---|---|
| `unit_id` | Synthesis unit the decision concerns |
| `report_ids` | Records compared, semicolon-separated |
| `decision` | `consolidated` or `kept_separate` |
| `basis` | Which of authorship, stated relation, method, data, experimental contribution drove the decision |
| `fields_taken_from` | For a consolidated unit, which report supplied the experimental fields |
| `rationale` | One or two sentences |

### 1.3 Evidence requirement

Every coded field has a companion `<field>_source` holding a locator in the
primary source — section number, figure, table, or page — and, where short, the
verbatim sentence supporting the code.

- Values are **never** inferred from software frameworks, architectural
  conventions, or what implementations of this kind usually do.
- If the locator cannot be written, the field is `NR`, not a guess.
- Coder judgement beyond the quoted text belongs in `notes`, never in the value.

---

## 2. Universal value conventions

| Code | Meaning |
|---|---|
| `NR` | The indicator applies to this study, but the source does not report it, or reports it too vaguely to code. |
| `NA` | The indicator does not conceptually apply to this study design. |

**`NR` vs `NA` — decision rule.** Ask: *could this study have reported the field?*
Yes, but it did not → `NR`. No, the field is meaningless for this design → `NA`.

Worked cases:

- Purely theoretical contribution, no seeds to report → `multiple_runs = NA`.
- Continuous-variable model, no qubit count → `qubits_* = NA`.
- Implemented model whose paper never states circuit width → `NR`.
- Classical diffusion model generating circuits → `qubits_generator_* = NA`, but
  `qubits_target_circuit` is coded.

Never write a combined `NR/NA`. Every cell resolves to exactly one.

---

## 3. Identity and chronology

| Field | Values | Definition |
|---|---|---|
| `unit_id` | string | Stable identifier (BibTeX key of the primary report). |
| `reports` | list | All records consolidated into this unit. |
| `title`, `authors` | string | Of the primary report. |
| `first_disclosure_year` | integer | Earliest included public disclosure of the unit. |
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
and stop at the first that fires. Record which one fired in
`primary_class_rule_fired`.

> **R1 — Generated object outranks diffusion space.**
> If the main contribution is generating quantum circuits, gate sequences,
> ansatzes, or variational parameters, and the diffusion process itself is
> predominantly classical → `circuit_param_synthesis`.
> *The quantum element is the output, not the computational engine.*

> **R2 — Physical noise as a resource.**
> If device noise or hardware randomness supplies the generative mechanism
> rather than degrading it → `quantum_noise_driven`.

> **R3 — Learned compression outranks the diffusion space.**
> If diffusion or generation happens inside a learned compressed representation,
> and that representation is central to the contribution **and** to its
> evaluation → `quantum_latent`, even when the objects diffused are quantum
> states.

> **R4 — Diffusion space.**
> If perturbation or recovery acts directly on states, channels, trajectories,
> measurement distributions, or CV systems → `quantum_native`.

> **R5 — Function of the quantum element.**
> If a PQC performs denoising, conditioning, feature extraction, or correction
> inside a classical-data pipeline → `hybrid_denoiser`.

> **R6 — Residual.** Otherwise → `theory_foundations`.

**Why R3 precedes R4.** A learned compressed representation changes the space in
which diffusion is computed, and therefore the evidence needed to interpret the
result: the encoder and decoder are part of the generative pipeline and of its
cost. Without this ordering, the decision flow sends every study diffusing over
quantum states to `quantum_native` and cannot reproduce a latent state-generation
unit.

**Centrality test for R3.** The representation is central when *both* hold:
(i) the paper's main methodological claim concerns the compressed representation
or the module acting inside it; and (ii) the reported evaluation is performed on
outputs produced through that representation. A latent variant reported as one
ablation among others does not satisfy the test.

**Validation requirement.** After coding, a second person re-derives
`primary_class` for every unit from R1–R6 alone, without seeing the recorded
value. A disagreement is either coder error or a gap in the rules; a gap is fixed
here and the whole corpus is re-derived. The manuscript reports how many units
were re-derived and how many matched.

### 4.3 `quantum_role`

A one-sentence prose rendering of the primary class, used in the study-level
table. It is a controlled vocabulary of six values in one-to-one correspondence
with `primary_class`, and is therefore derived, never coded independently:

| `primary_class` | `quantum_role` |
|---|---|
| `quantum_native` | Quantum states/channels form the diffusion space |
| `circuit_param_synthesis` | Quantum circuit or parameters are the generated output |
| `hybrid_denoiser` | PQC/QNN performs denoising, conditioning, or feature processing |
| `quantum_latent` | Quantum module operates in the learned latent representation |
| `quantum_noise_driven` | Physical quantum noise/random walk supplies forward corruption |
| `theory_foundations` | Quantum score reversal is the object of theoretical analysis |

If a coder wants to write a seventh sentence, the classification is wrong or the
class list is incomplete. Resolve that before editing this table.

### 4.4 `secondary_descriptors`

Multi-label; never changes `primary_class`. Each label has its own trigger, and
a label is applied only when the paper's own framing supports it.

| Label | Applied when |
|---|---|
| `conditional` | The reverse process is explicitly conditioned on auxiliary information (class label, Hamiltonian, measurement record, problem instance, target property). |
| `score_based` | The method is formulated through a score function or an SDE/ODE formulation, rather than only as a discrete-time DDPM. |
| `latent` | A compressed representation is used anywhere in the pipeline, including when R3 did not fire. |
| `measurement_based` | Measurement outcomes drive the forward or reverse dynamics, rather than only reading out a result. |
| `open_system` | The forward or reverse process is described through channels, Kraus operators, or a master equation. |
| `continuous_variable` | The model operates on continuous-variable modes rather than qubits. |
| `hardware_oriented` | The paper presents execution on, or adaptation to, physical devices as part of its contribution — not merely a closing demonstration. |
| `theoretical` | The paper establishes analytical results, whether or not `primary_class` is `theory_foundations`. |

---

## 5. Generative objective — **goes in the paper**

`generative_objective` separates aims that are not comparable and must not be
pooled into one performance narrative.

| Value | Definition | Typical evaluation |
|---|---|---|
| `state_generation` | Produce quantum states matching a target state or family. | Fidelity, trace distance |
| `distribution_learning` | Learn a distribution over states or classical data and sample from it. | MMD, Wasserstein, FID, KID |
| `state_restoration` | Recover a state corrupted by a known or learned noise process. | Fidelity against the pre-corruption state |
| `classical_data_generation` | Produce classical data (images, time series, features). | FID, IS, SSIM, task metrics |
| `circuit_synthesis` | Produce circuits, gate sequences, ansatzes, or parameters. | Validity, novelty, resources, task performance |
| `theoretical` | No generated artifact. | `NA` |

**Rule.** Restoring a corrupted state is *not* evidence of state generation, and
generating one state is *not* evidence of having learned a distribution.
`generative_objective` records the objective the headline claim rests on;
`secondary_objectives` is multi-label and records the others.

Secondary objectives are carried because several units genuinely do two things —
a paper titled for both state generation and restoration, or a noise-inversion
method evaluated by downstream task accuracy. Dropping them would represent such
studies by half.

Quantitative comparison is reported only within a shared
(`generative_objective`, dataset or target family) pair.

---

## 6. Experimental scale — qubit fields

### 6.1 Why the split — **goes in the paper**

A single "qubits" column mixes quantities that mean different things: the width
of the generative circuit, its ancillas, the width of a circuit the model
*produced*, and the width of a downstream task used only for evaluation. Reported
together they overstate the demonstrated generative scale.

| Field | Counts | Excludes |
|---|---|---|
| `qubits_generator_sim` | Widest circuit at which **generation was demonstrated** end to end, in classical simulation. | Ancillas; forward-only tests; generated target circuits; downstream evaluation. |
| `qubits_generator_hw` | Same, executed on a physical device. | Idem. |
| `qubits_forward_only` | Widest circuit at which only the forward or corruption process was implemented, when wider than the demonstrated generation. | Any configuration that produced a generated output. |
| `qubits_ancilla` | Ancillas for readout, Hadamard tests, conditioning, or time embedding. | Data qubits. |
| `qubits_target_circuit` | Width of the circuit the model *generates*, for synthesis studies. | The generator, which is classical in these studies. |
| `qubits_downstream_eval` | Width of a circuit used only to evaluate a generated artifact on a later task. | Everything the generative model itself runs. |

**Which field feeds the scale figure:** `qubits_generator_sim` and
`qubits_generator_hw`, as separate series. No other qubit field enters the scale
synthesis, and qubit fields are never summed.

**Why generation rather than the widest implemented process.** The scale figure
reports how far generation has been demonstrated, so a width at which only the
forward process was exercised does not belong in it: running a corruption
process over a wide register shows that the register can be prepared and
perturbed, not that the model can generate at that width. Such widths are
recorded in `qubits_forward_only`, stated in the study-level table, and excluded
from the series.

**Generated-circuit width is reported separately.** For circuit- and
parameter-synthesis studies, `qubits_target_circuit` is real and relevant
information, but it describes the object produced, not the scale of the
generative model. It is reported in its own series or figure, labelled as the
width of the generated circuit, and never merged into the generator series.

### 6.2 Common rules

- Code only what is explicitly reported or unambiguously determined from the
  implemented experiment.
- When several sizes are evaluated, record the **maximum size at which the
  reported output was actually produced** in that execution context, and keep
  the full range in `qubits_range`.
- When the forward process is exercised at a wider register than the widest
  demonstrated generation, the generation width goes in `qubits_generator_*`
  and the wider forward width goes in `qubits_forward_only`. Both appear in
  `qubits_range`, and `notes` states which is which.
- Continuous-variable models: `NA`, not `NR`.

### 6.3 `qubits_confirmed`

`yes` | `no`. `no` marks a value the source discusses as a scalability
projection without establishing that it was implemented. Unconfirmed values are
excluded from the quantitative scale synthesis and reported separately.

### 6.4 Interpretation guard

Fewer parameters, or more qubits, taken in isolation, demonstrate neither
efficiency nor quantum advantage. A resource claim is coded only when the source
states a like-for-like comparison, and its terms go in `resource_claim_basis`.

---

## 7. Execution setting

### 7.1 `hardware_stage` — **goes in the paper**

Which stage of the pipeline ran on a physical device. Multi-label.

| Value | Definition |
|---|---|
| `none` | Everything in classical simulation, including noisy simulators and emulated device backends. |
| `forward_on_device` | The forward/corruption process ran on hardware; the reverse model was trained offline on the resulting data. |
| `training_in_loop` | Circuits were executed on the QPU during training, inside the optimisation loop. |
| `sampling` | Device used to draw samples from a trained model. |
| `inference` | Device used for forward passes at evaluation time. |
| `post_training` | Device used for a demonstration after training, outside the training and reported-metric pipeline. |

`forward_on_device` is kept as its own value rather than folded into
`training_in_loop`: hardware produced the training data, but no circuit ran
inside the optimisation loop. Merging them would overstate optimisation on
hardware.

**A noisy simulator or an emulated backend is `none`.** It models a device; it is
not one.

**Crosswalk from the prose values used before v2.2:**

| Previous prose value | v2.2 |
|---|---|
| None | `none` |
| Post-training sampling/generation | `post_training`, `sampling` |
| Post-training generation | `post_training` |
| Post-training hardware demonstration | `post_training` |
| Inference/evaluation | `inference` |
| Inference | `inference` |
| Forward noise/random-walk process | `forward_on_device` |

### 7.2 `training_locus` — **goes in the paper**

Where optimisation of the model's parameters happened. This is the field that
supports any statement about training on hardware.

| Value | Definition |
|---|---|
| `classical_simulation` | All circuit evaluations during training were simulated. |
| `hybrid_in_loop` | A classical optimiser drove parameters while circuits ran on the QPU during training. **Real hardware participation in training.** |
| `end_to_end_hardware` | The full training loop, including optimisation, executed on quantum hardware. |
| `not_trained` | Analytical or training-free method. |
| `NA` | Theoretical contribution. |

**Rule.** A claim that no study trains on hardware must be stated against
`end_to_end_hardware`. `forward_on_device` means hardware produced the training
data, which is neither `hybrid_in_loop` nor `end_to_end_hardware`; say which one
is meant.

### 7.3 Other execution fields

| Field | Values | Notes |
|---|---|---|
| `simulator` | string \| `NR` \| `NA` | Name and version where stated. Record the platform, not just "classical simulator". |
| `device` | string \| `NR` \| `NA` | Named backend. `NR` when a device is used but unnamed. |
| `noise_model` | string \| `none` \| `NR` | |
| `shots` | string \| `NR` \| `NA` | Record the quantity as reported; `shots_basis` says what it counts (per circuit, per state, total). Where the source is internally inconsistent, record the inconsistency in `notes` rather than picking one. |
| `depth` | string \| `NR` \| `NA` | In the architectural unit the source uses, stated in the value. Not standardised across studies. |
| `circuit_evaluations_per_sample` | integer \| `NR` \| `NA` | Circuit executions along the reverse trajectory, where derivable. |

---

## 8. Evaluation and comparison

### 8.1 `classical_baseline`

`yes` | `no` | `na`

`yes` requires an explicit comparison against a non-quantum comparator
addressing the **same task objective**. Random parameter initialisation, random
search, and randomly generated ansatzes count when used as explicit comparators.

- A resource-budget mismatch between method and comparator is a **limitation**,
  recorded in `baseline_resource_match`, not a reason to code `no`.
- Comparison only against other quantum models is `no`.
- `na` only for units with no empirical evaluation.

### 8.2 `multiple_runs`

`yes` | `no` | `na`. `yes` requires explicitly documented multiple seeds or
independent runs.

**Not independent repetitions:** measurement shots; multiple samples from one
trained model; folds from the same training procedure; a single reported seed.

### 8.3 `uncertainty_reported`

`yes` | `no` | `na`. Standard deviations, confidence intervals, box plots, or
comparable dispersion measures.

### 8.4 `metrics` and `metric_families`

Metric names are recorded **as reported**; `metric_families` holds the normalised
family. The mapping below covers every name in the corpus and is the reference
for new ones.

| Family | Metric names |
|---|---|
| `image_quality` | FID; Inception Score; KID; SSIM; PSNR; LPIPS |
| `distributional_similarity` | Wasserstein distance; MMD; MMD/CMMD; KL / JS divergence; Statistical moments; Physics-domain distribution metrics; Precision / recall *(generative coverage sense)* |
| `quantum_state_quality` | Fidelity / overlap; Superfidelity; Trace distance; Expectation / observable error; Subspace occupancy |
| `task_performance` | Task accuracy; ROC-AUC; Success rate; MSE; RMSE / MAE; Precision / recall / F1 *(downstream classifier sense)* |
| `circuit_quality` | Circuit validity; Circuit novelty / uniqueness |
| `computational_resources` | Circuit resources; Parameter count |
| `optimization_behaviour` | Energy / approximation ratio; Optimization convergence; Initial loss |
| `uncertainty` | Statistical uncertainty |
| `NA` | Theoretical bounds |

**Ambiguous names — decision rules.**

- **Precision / recall.** Measured on the distribution of generated samples
  (coverage and fidelity of the generated set) → `distributional_similarity`.
  Measured on a downstream classifier's predictions → `task_performance`. The
  source's own description decides.
- **Energy / approximation ratio, Optimization convergence, Initial loss.**
  These describe how an optimisation behaved once seeded with the generated
  artifact, not how well the artifact performs a task, and they form their own
  family, `optimization_behaviour`. They appear in 3 units, all of them
  circuit- or parameter-synthesis studies, where the generated object is an
  initialisation rather than an answer. Keeping them apart from
  `task_performance` prevents "the optimiser converged faster" from being read
  as "the task was solved better".
- **Subspace occupancy** characterises the generated state ensemble, not a
  classical distribution → `quantum_state_quality`.

**Name normalisation.** Record the source's name, but normalise spelling
variants of the same quantity to one string. The corpus currently contains both
"KL / JS divergence" and "Jensen-Shannon divergence" for the same family of
measure; the recode collapses them to `KL / JS divergence` and notes the
source's exact wording in `metrics_source`.

**Training-objective flag.** A quantity reported only as a training objective is
listed in `training_objective_only` so that it is not read as a final evaluation
measure.

Recording that a metric was used is separate from judging it adequate for the
claim; adequacy commentary belongs in the synthesis, not in this field.

### 8.5 `input_interface`

Multi-label; `NR` when a quantum model exists but its encoding is not stated;
`NA` when the pipeline has no quantum input interface.

| Value | Definition |
|---|---|
| `amplitude_encoding` | Classical vector written into the amplitudes of a state. |
| `angle_rotation_encoding` | Classical values written into rotation angles of single-qubit gates. |
| `native_quantum_state` | The model consumes quantum states directly, with no classical-to-quantum encoding step. |
| `basis_position_encoding` | Classical values written into computational-basis strings or positions. |
| `data_reuploading` | The same classical input is re-encoded at several circuit layers. |
| `phase_encoding` | Classical values written into relative phases. |
| `quantum_autoencoder_vq_latent` | Input reaches the circuit through a learned quantum autoencoder or vector-quantised latent. |

### 8.6 `readout_strategy`

Multi-label; same `NR`/`NA` convention.

| Value | Definition |
|---|---|
| `computational_z_basis_sampling` | Bitstrings sampled in the computational basis. |
| `pauli_z_expectation` | Expectation values of Pauli-Z observables. |
| `pauli_x_expectation` | Expectation values of Pauli-X observables. |
| `full_state_statevector_tomography` | Full-state access, whether by simulator statevector or by tomography. |
| `randomized_pauli` | Randomised Pauli measurements across bases. |
| `nonlocal_hadamard_test` | Overlap or non-local quantity read out via a Hadamard-test-style circuit. |
| `ancilla_projective_basis_unspecified` | Projective measurement on an ancilla whose basis is not stated. |
| `measured_basis_unspecified` | A measurement is described without identifying its basis. |

The last two are deliberate: they record an incomplete protocol rather than
forcing a guess, and they are what the synthesis counts as incomplete basis
information.

---

## 9. Generated object and dataset domain

### 9.1 `generated_object`

Controlled vocabulary, recorded at the level the study states:

`quantum_states` · `quantum_circuits_parameters` · `classical_images` ·
`remote_sensing_images` · `medical_images` · `classical_discrete_distributions` ·
`time_series` · `classical_features` · `scientific_particle_data` ·
`not_applicable`

### 9.2 Grouping for the taxonomy-by-object figure

The figure uses coarser categories. The grouping is fixed here so it is not
re-decided per figure:

| Figure category | Includes |
|---|---|
| Quantum states | `quantum_states` |
| Quantum circuits / parameters | `quantum_circuits_parameters` |
| Classical images | `classical_images`, `remote_sensing_images`, `medical_images` |
| Other classical data | `time_series`, `classical_features`, `scientific_particle_data`, `classical_discrete_distributions` |
| Not applicable | `not_applicable` |

### 9.3 Dataset domain grouping

For the benchmark-dataset figure, each dataset is assigned one domain:

| Domain | Datasets |
|---|---|
| Handwritten/fashion benchmarks | MNIST; Fashion-MNIST; scikit-learn Digits |
| Natural images | CIFAR-10 |
| Remote sensing | EuroSAT |
| Medical imaging | RFMiD |
| Particle physics | CMS Open Data quark/gluon jets |
| Financial time series | Apple stock; Amazon stock |
| Synthetic distributions | Bars-and-Stripes; mixed Gaussian synthetic distribution |
| Not reported | — |

A study using several datasets is counted once per dataset; the figure therefore
reports dataset adoption, not mutually exclusive study counts.

---

## 10. Reproducibility

| Field | Values | Rule |
|---|---|---|
| `public_code` | `yes` \| `no` \| `na` | `yes` only for code identified as publicly available at the search cut-off. An announced or planned release is `no`. |
| `code_url` | string \| `NR` | |
| `public_data` | `yes` \| `no` \| `na` | |

---

## 11. Double coding and agreement

Two coders extract independently. Disagreements are resolved by discussion, and
by a third coder when discussion does not settle them.

**Protocol.**

- **Subset:** 12 of the 39 synthesis units, about 30%, drawn at random with a
  recorded seed and stratified so that every `primary_class` appears at least
  once.
- **Statistic:** Cohen's kappa, computed per field, reported with the number of
  units and the number of categories in play.
- **Fields covered:** the categorical fields that carry the quantitative claims —
  `primary_class`, `generative_objective`, `hardware_stage`, `training_locus`,
  `classical_baseline`, `multiple_runs`, `public_code`, and the `NR`/`NA`
  distinction on the qubit fields.
- **Multi-label fields** (`hardware_stage`, `secondary_descriptors`,
  `input_interface`, `readout_strategy`) are scored per label, presence against
  absence, and the per-label values are reported as a range rather than averaged
  into one number.
- **Reporting:** the manuscript states the statistic, the subset size, the fields
  covered, and the resulting values. If a field's kappa cannot be computed
  because one category is constant across the subset, that is reported as such
  rather than omitted.

The taxonomy re-derivation of §4.2 is a separate check and is reported
separately: it tests whether the rules reproduce the class, not whether two
people agree.

---

## 12. Which fields appear in the manuscript

The complete codebook lives in the repository. These definitions carry the
manuscript's headline claims and must be visible to a reader who never leaves the
PDF:

1. **The qubit role split** (§6.1) — supports the reported scale range.
2. **`training_locus` and `hardware_stage`** (§7.1, §7.2) — support every
   statement about hardware execution and training.
3. **`NR` vs `NA`** (§2) — supports every denominator.
4. **The precedence rules R1–R6** (§4.2) — support the class counts.
5. **`generative_objective`** (§5) — defines which comparisons the synthesis
   is willing to make.

The normalised metric families (§8.4) are also stated in the manuscript, since
the metric figure is organised by them.

Suggested placement: a coding-conventions table in the methodology; an appendix
with the full field list; a pointer from the data-extraction section to this file.

---

## 13. Worked examples

The cases coders are most likely to stall on.

**A circuit-synthesis study with qubit numbers everywhere.**
A classical conditional DDPM generates QAOA parameters; the paper reports 16
qubits in QAOA evaluation and training cases up to 8.
→ R1 fires: `circuit_param_synthesis`. `qubits_generator_sim = NA` (the
generator is a classical network). `qubits_target_circuit = 8`.
`qubits_downstream_eval = 16`. The 16 does not enter the scale synthesis.
`generative_objective = circuit_synthesis`.

**A latent model that generates quantum states.**
Diffusion runs inside a learned compressed representation and the outputs are
quantum states.
→ R1 no, R2 no, R3 **yes** (the representation is central to both contribution
and evaluation) → `quantum_latent`, `primary_class_rule_fired = R3`.
`generative_objective = state_generation`.

**A study spanning quantum-native and hybrid-latent.**
A circuit-based model reported in both a full-quantum and a latent variant, with
classical images as output.
→ R3 is tested first and does **not** fire, because the latent variant is one
configuration among several rather than the central contribution; R4 fires →
`quantum_native`, rule R4. `secondary_descriptors` includes `latent`.

**Forward diffusion executed on hardware.**
Quantum-walk/noise forward process run on a physical backend; the reverse MLP is
trained offline on the resulting corrupted data.
→ `hardware_stage = forward_on_device`; `training_locus = classical_simulation`;
`multiple_runs = yes` when the paper documents repeated simulations per
configuration.

**A study whose hardware run has no stated width.**
Simulation at 9 qubits; a reduced architecture is executed on a named device
without stating its circuit width.
→ `qubits_generator_sim = 9`; `qubits_generator_hw = NR`; `device` named;
`hardware_stage = inference`. The unit contributes no hardware point to the
scale figure.

**Forward tests wider than the generation demonstration.**
Forward-diffusion tests at 12 qubits; the principal generated-state demonstration
reaches 4.
→ `qubits_generator_sim = 4` — the width at which generation was actually
demonstrated. `qubits_forward_only = 12`. `qubits_range` records both and
`notes` states which is which. Only the 4 enters the scale figure.

**An operational class with a fully theoretical execution profile.**
A study assigned to `circuit_param_synthesis` by R1 whose simulator, hardware
stage, baseline, and repetition fields are all `NA` on theoretical grounds.
→ This combination is contradictory and must be re-examined: either the study
has an implementation, in which case the execution fields are `NR` rather than
`NA`, or it does not, in which case R6 applies and the class is
`theory_foundations`. Do not leave the mixture in place.

---

## 14. Expected consequences of applying v2.2

Recoding under this version is expected to change reported values. Confirm each
during the recode rather than assuming it.

- **The scale range changes.** Every circuit- or parameter-synthesis study has a
  classical generator, so its recorded qubit value moves to
  `qubits_target_circuit` or `qubits_downstream_eval` and leaves the scale
  synthesis. The current maximum of 16, from a QAOA evaluation, is among them.
  Both the range and the number of contributing units will fall.
- **Class counts may shift** between `quantum_native` and `quantum_latent` once
  R3 is applied before R4 across the whole corpus.
- **The hardware narrative becomes more precise**, since `forward_on_device` is
  distinguishable from post-training demonstration and from optimisation in the
  loop.
- **Denominators may change** where a field moves between `NR` and `NA`.
- **Units whose widest register was a forward-only test now enter the scale
  figure at their demonstrated generation width**, which is lower.
- **The metric-family list grows from seven to eight** with
  `optimization_behaviour`. The manuscript's methodology section and the metric
  figure both state the families and must be updated together.
- **A separate series or figure reports generated-circuit width** for the
  synthesis studies, replacing their former presence in the generator series.

Figures 2, 4, 5, 6, 7, and 10 are regenerated from the recoded workbook, and
every count in the running text is re-derived from it rather than edited by hand.

---

## 15. Change log

| Version | Change |
|---|---|
| 2.0-draft | First written codebook: qubit roles split; `training_locus` and `hardware_stage` defined; `NR` separated from `NA`; ordered precedence rules R1–R6; `generative_objective` added; `*_source` locators required. |
| 2.2 | Eighth metric family `optimization_behaviour` separated from `task_performance`. Generator qubit fields redefined as the width at which generation was demonstrated, with `qubits_forward_only` added for wider forward-only tests. Generated-circuit width reported in its own series rather than in the generator series. No open decisions remain. |
| 2.1 | Precedence ordering fixed with R3 before R4, with a centrality test. `forward_on_device` confirmed as its own stage, with a crosswalk from the previous prose values. `secondary_objectives` retained. Agreement protocol specified (Cohen's kappa, 12 of 39, per-field). Added: metric-name to family mapping with ambiguity rules; triggers for every secondary descriptor; definitions for input and readout interfaces; controlled vocabulary for `generated_object` with figure grouping; dataset domain grouping; linkage-log format; `quantum_role` as derived from `primary_class`; worked examples; expected consequences. |

---

## 16. Remaining work

No coding decisions are open. Two tasks remain before this codebook becomes the
protocol of record:

1. **Confirm the `NR` entries on qubit counts.** Five units carry `NR` in the
   qubit column. Each needs checking against its source during the recode: an
   implemented study that does state a width should not stay `NR`.
2. **Publish the extraction workbook.** Only the evidence-indicator subset is
   currently in the repository. Publishing the full workbook, coded under this
   version, is what allows the manuscript to cite this codebook as the protocol
   that produced its tables.
3. **Produce the linkage log.** The format is specified in §1.2, but the file
   does not yet exist. It is written alongside the recoded workbook, and until
   then the manuscript should not state that a linkage log is supplied with the
   review artifacts.
