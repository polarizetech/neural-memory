# Habituation as memory — results (2026-09-23)

Minimal model: `neurotape.habituation`, preregistered in [`PREREG.md`](PREREG.md).

- 10 seeds per condition. Each seed is a different network *and* a different stored sound, relative sounds and novel null.
- Auditory-nerve periphery (Zilany 2014).
- **260 runs in total, 0 failed.**
- Raw reports, summaries and configs are in [`results/`](results/).
- Recognition = S(stored) − mean S(20 novel sounds), where S = suppression against a paired, time-matched naive control.
- "Top" = the stored sound ranked above all 20 novel sounds (p = 1/21).

## The answer in one paragraph

Repetition alone, with no neuromodulation, leaves a trace that is specific to the repeated sound. The trace can be read
straight from the synapses in every arm that has a mechanism. But whether the *network's response* recognises the sound
depends on where the trace is kept:

- **Presynaptic depletion** (short-term depression, or a presynaptic long-term rule) is kept per input fibre. It is
  therefore shared by every sound that uses that fibre, and it generalises: the stored sound is suppressed ~30–75 %,
  and novel sounds are suppressed almost as much. Recognition ≈ 0.
- **A per-synapse depression gated by the responding cell** (`hebb_only`) is specific. At the best of the three
  declared rates (×¼) it:
  - recognises the stored sound in **10/10 seeds** after 16 presentations;
  - is still above chance **30 minutes later** (+0.031 [+0.021, +0.042]);
  - survives 20 s of other sounds;
  - grows with the number of presentations ("it takes a few times": +0.050 after 1, +0.129 after 16).

  What it keeps is the **spectrum and not the order**. A time-reversed copy is exactly as familiar, a 1/6-octave shift
  is partly familiar, and a 1/2-octave shift is not.

**Recalling it through the network works.** A flat noise probe played to the trained network comes back with a dip
shaped like the stored sound: a negative afterimage. That dip identifies the stored sound among 21 candidates in
9/10 seeds, **30 minutes after training**.

**Salience (step 3) did not give an interpretable answer.** The network-driven salience loop ran away in 3/10 seeds,
and no arm showed dishabituation. See below.

## Criterion by criterion

| id | criterion (PREREG) | result | verdict |
|---|---|---|---|
| N0 | `none` recognition 0 everywhere | exactly 0 in every cell (identical inputs + noise drive both copies to the same trajectory) | **holds** |
| H1 | `std`, 2 s, N=16: CI > 0 and top ≥ 8/10 | +0.004 [−0.012, +0.020], 0/10 | **fails** |
| H1-dose | `std`: rec(16) − rec(1) > 0 | +0.004 vs −0.008, CIs overlapping | **fails** |
| H1-fade | `std`: 0 at 300 s and 1800 s | exactly 0 | **holds** (trivially — nothing to fade) |
| H2 | `std_hebb`/`std_presyn`, 1800 s: CI > 0 | +0.001 [−0.024, +0.026] / +0.000 [−0.010, +0.010] | **fails**, at all three rates for `std_hebb` |
| H2-interf | same, interf | fails | **fails** |
| — | **`hebb_only` (not named in H2)** | ×1: +0.011 [−0.006, +0.028] at 1800 s; **×¼: +0.031 [+0.021, +0.042]** (4/10 top); ×4: saturated, 0 | reported, **not** a preregistered pass |
| K-order | reversed ≈ stored, > 0 | `hebb_only` ×1, 2 s: +0.063 vs +0.064; ×¼, 1800 s: +0.030 vs +0.031 | **holds** |
| K-shift | 1/6 > 1/2, 1/2 contains 0 | `hebb_only` ×1: +0.046 / −0.006; ×¼: +0.097 / −0.014 | **holds** |
| F-engram | top ≥ 8/10, N=16, 2 s | `std` 10/10, `std_presyn` 10/10, `std_hebb` 8/10, `hebb_only` 9/10 | **holds** |
| F-after | afterimage top ≥ 8/10 | `hebb_only` 8/10 (×1), 8/10 (×¼, 2 s) and **9/10 at 1800 s (×¼)**; `std` 2/10, `std_hebb` 5/10 | **holds for `hebb_only` only** |
| R1 | decrement, ρ < 0 in ≥ 8/10 | 10/10 in every arm with a mechanism | **holds** |
| R2 | spontaneous recovery | `std` S(stored) 0.309 at 2 s → 0.023 at 30 s | **holds** |
| R4 | shorter ISI → deeper decrement | R16/R1 0.44 / 0.54 / 0.67 at ISI 2 / 3 / 8 s, CIs disjoint | **holds** |
| H3 | `network\|salient` NM falls, `raw` flat | `network\|salient` **ran away** in 3/10 seeds (NM > 200, up to 119 000 spikes); `raw\|salient` fell 1.12 → 0.78 (ratio 0.69, fails "flat") | **uninterpretable / fails** |
| H4-write, H4-recall | NM-gated write flips; salience not recalled | depend on H3 | **uninterpretable** |
| R8 | dishabituation in `raw`/`network` | DI cycle 1: `off` −0.048, `raw` −0.073, `network` +0.022 (all CIs ≤ 0 or containing 0) | **fails** |
| R9 | dishabituation habituates | needs R8 | **not testable** |

## What the failures say, and one exploratory arm

- **Why presynaptic habituation generalises.** After 16 presentations (seed 0), channels the stored sound barely used
  were depleted 21 % against 30 % for the ones it used. Auditory-nerve footprints at 60 dB are broad: 61 % of CFs sit
  above 20 % of each sound's maximum, and stored/novel footprints correlate at 0.32 on average.
- **Exploratory, post hoc: depleting the slow pool per spike instead of per release.** This was added because release
  saturates. It made habituation much stronger (S 0.73) and **no more specific** (recognition −0.022, 0/10). So my
  per-release choice was not the cause; where the trace is stored was.
  ([`results/EXPLORATORY_slow_per_spike/`](results/EXPLORATORY_slow_per_spike/))
- **The long-term rate has a window.** At ×4, silence alone drives every synapse to the floor within the 30-minute
  delay, and the contrast goes with it. ×¼ is best of the three tested. Nothing between them was run, and nothing
  below ×¼.
- **Step 3's runaway is a model defect, not a finding.** The NM gain was calibrated with its effects switched off.
  Once switched on, NM → input gain → response → NM has a loop gain above 1 and nothing bounds it.
- **Step 3's missing dishabituation has two causes.**
  - The loud dishabituator also depletes channels it shares with the stored sound.
  - NM decays with τ = 0.5 s, so its boost has gone before the stored sound arrives 3 s later.
- **`raw` salience "fading" is its onset detector's 1 s baseline not resetting within a 3 s spacing.** It happens
  entirely between presentations 1 and 2; from 2 to 16 the ratio is 0.975 [0.937, 1.013].

## Limits, stated so nobody has to discover them

- **`hebb_only` has no short-term depression, and so it transmits much more.** Its naive response is 2012 spikes
  against ~470 with depression, and its long-term rule is correspondingly more engaged. The rate criterion (C3) was set
  with depression on.
- The positive memory result comes from an arm the preregistration did not name for H2, at one of three declared
  rates. It is a result to replicate, not a confirmation.
- "30 minutes" is set by placeholder values: the long-term recovery time (1 h) and the rate. The 1 h value was not
  swept (declared, not run).
- **What the trace stores, and what it doesn't.**
  - It stores a spectral footprint and cannot store temporal order: the reversed sound is always as familiar as the
    original.
  - So this is recognition memory for "what it sounds like", not a recording.
  - It says nothing about whether *all* memory works this way: there is no recurrence, no hippocampus and no second
    modality.
- No sound has been listened to. The model has never been compared with a recording of real habituation.
