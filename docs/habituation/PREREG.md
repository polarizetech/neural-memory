# Habituation as memory — preregistration (written 2026-09-23, before any recognition readout existed)

**The operator's question.** Is habituation a form of memory, possibly the form, with neuromodulation
(salience) as something that is itself habituated? Concretely:

1. Repetition alone, with no neuromodulation, stores something specific to the repeated sound.
2. That trace lasts, i.e. it is memory rather than a buffer.
3. Salience fades with repetition *because* the response that drives it habituates.
4. What is stored with salience attached fades as salience fades.

**Scope, stated once.** A positive result shows habituation is *sufficient* to store something in this
network. It cannot show that it is how all memory works. The model has no hippocampus, no recurrence and no
consolidation machinery; it was stripped to make one mechanism testable.

## The model (frozen for these runs)

`neurotape.habituation`, configured by `configs/habituation.yaml`:

- Auditory nerve: Zilany et al. 2014, via `cochlea`.
- A phenomenological low-spontaneous relay.
- Tonotopic relay→E synapses with two-timescale short-term depression.
- Conductance LIF cells: 200 E, 50 I, with E→I→E inhibition.
- Parameters and sources: `ASSUMPTIONS.md` § *Minimal habituation model*.

Operating-point criteria, the only things parameters were set against:

| criterion | value | result |
|---|---|---|
| C1 spontaneous E rate | 0.2–2 Hz | 0.29 Hz |
| C2 naive response to a novel 60 dB sound | ≥ 3× spontaneous, ≥ 30 % of E cells active | 4.7× (rate periphery), 5.4× (AN); 71 % / 89 % |
| C3 anti-Hebbian long-term rule engaged, not saturated | stored-channel L after 16 presentations in 0.70–0.95 | 0.87 (`eta_hebb` 0.05) |
| C4 presynaptic long-term rule | derived: spontaneous release alone holds L at 0.8 | `eta_pre` computed, not chosen |
| C5 salience | NM gain solved per run and per mode so loud (+15 dB) calibration sounds peak at NM = 1.0 in a naive network | exact by construction |
| C6 NM-gated potentiation | `eta_pot` = 2 × `eta_hebb`: at NM = 1, a synapse at L = 1 potentiates as strongly as a neutral one depresses | a definition, not a fit |

**What I saw before writing this.**

- **Operating point:** per-presentation responses to one stored sound (seed 0). The decrement was visible (406 → 293 over 10 presentations).
- **C3:** stored-channel L trajectories.
- **Salience calibration** (seed 0, rate periphery), NM peak across 16 presentations of a loud stored sound:
  - `raw`: ≈ 1.0 throughout;
  - `network`: 0.89, 1.08, 0.15, 0.26, 0.13 at presentations 1, 2, 4, 8, 16.
  - That is a single-seed preview of H3's measure.
- **No parameter was changed after it.** `eta_pot` was fixed by the C6 rule before this preview.
- **No recognition, fingerprint, delay or dishabituation readout had been computed.**

## Readouts (`habituation/measure.py`)

Every probe is presented to its own copy of the network. The control is the naive network carried
through the same delay and interference, then given identical relay spikes and membrane noise.

- **S(x)** = 1 − R_trained(x) / R_control(x): total E spikes over the probe plus 0.3 s.
- **Recognition** = S(stored) − mean S(novel), where the null is 20 novel sounds from the same generator.
  "Top" = stored ranked above all 20 (p = 1/21).
- **What is kept:** S(reversed) − null, S(shift 1/6 oct) − null, S(shift 1/2 oct) − null.
- **Fingerprint:** correlate a per-CF deficit with each candidate's spectral footprint, and rank the stored
  sound among 21 candidates.
  - *Engram:* the deficit is read from synaptic efficacy directly. No animal could read this.
  - *Afterimage:* the deficit is the network's suppressed response to a flat noise probe.

Aggregation: 10 seeds, each a different network *and* a different stored sound, relatives and null.
Mean with 95 % t-CI. "Holds" means the whole CI is on the stated side of zero.

## Hypotheses and criteria — `exp hab_memory` (steps 1–2, NM off)

Arms:

- `none`: no depression, no long-term rule. This is the instrument null.
- `std`: two-timescale depression only.
- `std_presyn`: `std` plus presynaptic long-term depression.
- `std_hebb`: `std` plus anti-Hebbian long-term depression.
- `hebb_only`: the long-term rule without short-term depression.

Grid: N ∈ {1, 2, 4, 8, 16}; delay ∈ {2, 30, 300, 1800} s silent. Delays ≥ 30 s are also run with 20 s of
other sounds first ("interf").

| id | claim | criterion (all at 10 seeds) | predicted |
|---|---|---|---|
| **N0** | the instrument is null without a mechanism | `none`: recognition CI contains 0 in every cell | holds |
| **H1** | repetition alone stores something stream-specific | `std`, 2 s: recognition CI > 0 at N = 16, **and** stored top in ≥ 8/10 seeds | holds |
| **H1-dose** | "it takes a few times" | `std`, 2 s: recognition(16) − recognition(1) CI > 0 | holds |
| **H1-fade** | short-term habituation is a buffer, not memory | `std`: recognition CI contains 0 at 300 s and 1800 s (N = 16) | holds (τ_slow = 20 s) |
| **H2** | a long-term habituation rule makes it memory | `std_hebb` and/or `std_presyn`: recognition CI > 0 at 1800 s, N = 16, silent | open; `std_presyn` predicted weak (spontaneous release competes) |
| **H2-interf** | …and it survives other sounds | same, interf | open |
| **K-order** | the trace holds spectrum, not temporal order | best arm, 2 s and 1800 s: S(reversed) − null CI overlaps recognition's CI, **and** is > 0 | holds (synaptic depletion has no memory of order) |
| **K-shift** | the trace generalises by spectral distance | shift 1/6 − null > shift 1/2 − null (means), and shift 1/2 CI contains 0 | holds |
| **F-engram** | the synapses hold a readable spectral fingerprint | best arm, N = 16, 2 s: engram rank 1 in ≥ 8/10 seeds | holds |
| **F-after** | the network can *express* it: noise → negative afterimage | same, afterimage rank 1 in ≥ 8/10 seeds | open |
| **R1** | decrement with repetition (Rankin 1) | per-presentation response Spearman ρ < 0 in ≥ 8/10 seeds, arms with depression | holds |
| **R2** | spontaneous recovery (Rankin 2) | `std`: S(stored) at 30 s < at 2 s (means) | holds |

## `exp hab_isi` — Rankin characteristic 4 (`std_hebb`, ISI 2 / 3 / 8 s)

| id | claim | criterion | predicted |
|---|---|---|---|
| **R4** | more frequent stimulation → more pronounced decrement | ratio R16/R1 at ISI 2 s < at 8 s (CIs disjoint) | holds |

## Hypotheses and criteria — `exp hab_salience` (step 3)

Common settings:

- Substrate `std_hebb`.
- NM has two effects: input gain and gating of potentiation (a dual-process arrangement).
- NM drive is `raw` (the unadapted input) or `network` (the E population's own response).
- Training is on the stored sound at +15 dB (`salient`) or at 60 dB (`neutral`); probes are at the training level.
- Delays are 30, 300 and 1800 s, silent.

| id | claim | criterion | predicted |
|---|---|---|---|
| **H3** | salience fades with repetition *because* the response habituates | `network\|salient`: NM(16) − NM(1) CI < 0 **and** `raw\|salient`: NM(16)/NM(1) CI contains 1 or lies above 0.8 | holds |
| **H4-write** | what is written flips as salience fades | `network\|salient`: stored-channel L after presentation 1 > 1 (potentiated) and after 16 < L after 1; `raw\|salient`: L after 16 ≥ L after 1 | holds, **largely by construction** once H3 holds (the write is NM-gated) — the content is the timing |
| **H4-recall** | salience is not recalled the same after repetition | `network\|salient`, 30 s: NM(stored probe) − NM(novel probes) CI < 0 at N = 16 | holds |
| **R8** | dishabituation (Rankin 8) | `raw` and `network`: DI cycle 1 CI > 0; `off`: DI cycle 1 CI ≤ 0 or containing 0 | holds |
| **R9** | dishabituation habituates (Rankin 9) — the operator's "salience loses potency" | `network`: DI5 − DI1 CI < 0; `raw`: contains 0 | holds |

## What would count against the operator's hypothesis

- **H1 fails:** repetition alone stores nothing specific, even at 2 s.
- **H1 holds, H2 fails:** habituation here is a buffer and never a memory.
- **H3 fails, i.e. `network` salience does not fade:** salience-fading is not habituation showing itself, at least in this model.
- **R9 fails under `network`:** dishabituation does not habituate.

Each outcome goes in the report whichever way it lands.

## Declared but not in the first pass

- A sweep of `eta_hebb` ×¼ and ×4, to show the H2 answer is not a property of one rate.
- The same sweep of `tau_s` (3600 s → 600 s and 6 h).
