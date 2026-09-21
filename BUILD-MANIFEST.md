# BUILD MANIFEST — neurotape

> **Adoption flows one way.** Nothing here raises any claim's tier. A working build is not a controlled test.

## What this project is exploring

Whether a spiking network with synaptic tagging and capture can store *time-varying waveforms* and
return them from its own activity — and which of its mechanisms, if any, do measurable work.

## What this build is trying to establish

| Concept / claim | What this build asks | What would count as an answer | What a null would mean |
|---|---|---|---|
| **no claim of its own** — `research/` has no corpus project for computational memory models (a gap, not an oversight). Nearest concept: **`C-0014`** (behavioural tagging capture works at an *offset*, `CITED`) | Does recall-phase activity, read by a decoder fitted on encoding only, reconstruct the stored stream better than (a) each single-mechanism ablation and (b) an echo state network of equal size? | the whole 95 % CI of (full − comparison) above zero over ≥ 10 seeds | STC stores *which cells*, not *when*: a rate-pattern memory does not carry a waveform, and the mechanisms are decorative for this task |

A build result is `[C-n1]` at best, and here it is not even that: it is a statement about a **model**.

## Adopted — behaviour depends on it

| Element | Source | Adoption | Read depth | Why |
|---|---|---|---|---|
| calcium early phase + tagging and capture | Luboeinski & Tetzlaff 2021, doi:10.1038/s42003-021-01778-y | `ADOPTED` | full text + authors' code | the storage mechanism under test |
| NM-dependent protein-synthesis threshold | Lehr, Luboeinski & Tetzlaff 2022, doi:10.1038/s41598-022-22430-7 | `ADOPTED` | full text + authors' code | reproduced first (experiment 5) |
| T-type Ca kinetics | Destexhe et al. 1996 (ModelDB 3343) | `ADOPTED` | mod file read; paper from memory | `g_T` is ours |
| auditory-nerve front end | Zilany, Bruce & Carney 2014 via `cochlea` (GPL-3) | `ADOPTED` | package run; paper from memory | |
| evoked-vs-oscillator phase-concentration benchmark | Doelling et al. 2019, doi:10.1073/pnas.1816414116 | `TRIAL` | full text | human MEG vs a 250-cell model: a shape comparison only |

## Related, NOT tested

| Concept | Relation | What this build does NOT do |
|---|---|---|
| `C-0014` — behavioural tagging works at an offset (−1 h, +15 min–2 h), fails at 0 h | the synaptic tag-and-capture model here (Luboeinski & Tetzlaff 2021) is the mechanism that literature rests on, and `NM(t)` with a configurable post-encoding level is where an offset would be imposed | it never varies the timing of a neuromodulator event relative to encoding, so it says **nothing** about `C-0014`. An NM-timing sweep is the experiment that would; Lehr et al. 2022 Fig. 4 is its published counterpart |

## Parked

| Element | Why parked |
|---|---|
| CoNNear inversion playback | TensorFlow + non-commercial weights; operator decision before download |
| cnmodel brainstem stage | needs NEURON |
| retina / video front end | later milestone by the brief's own ordering |

## Shared tools consumed

`tools/paper-library` (sources), `tools/universal-wave-translation-layer` (`uwtl.surrogates.iaaft`),
`tools/result-provenance` (stamps). None is modified by this project.
