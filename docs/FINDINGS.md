# FINDINGS — neural-memory, as of 2026-09-24 (project paused)

Every result below is a statement about **these models**, with their chosen parameters. None is evidence about
tissue, animals or people. Details and numbers live in the linked reports; this file is the map.

## TL;DR

- **As a tape it fails.** Recall is at chance in every condition. Its one positive (which stream dominated can be
  read from the rank order of cells) is measured *during encoding* and mostly reflects the input itself (§1–3).
- **Specificity comes only from per-synapse, postsynaptically gated plasticity.** Presynaptic depletion, in every
  form tried, generalises to any sound that shares its input fibres. This holds across the habituation steps, E01
  and E02.
- **A published single-cell habituation model (Rajan & Marshall 2025), run with its own rates, drains untrained
  responses under a synthesis block.** The organism does not. The gap is the model's output threshold, which a
  graded network lacks.

| Part | Where | Verdict |
|---|---|---|
| 1. Waveform tape (encode → store → recall) | [`docs/results/RESULTS.md`](results/RESULTS.md) | does not work; rank-order code is the one positive |
| 2. Storage diagnostic, P0–P3 | CLAUDE.md § Storage diagnostic | what is written is set by who fires, not by the stimulus |
| 3. Luboeinski & Tetzlaff 2021 reproduction | [`docs/repro/REPORT.md`](repro/REPORT.md) | the reference passes; neurotape recalls only with the paper's LIF cell |
| 4. Minimal habituation model, steps 1–3 | [`docs/habituation/RESULTS.md`](habituation/RESULTS.md) | only `hebb_only` recognises; step 3 uninterpretable |
| 5. E01-stentor-map | [`experiments/E01-stentor-map/RESULTS.md`](../experiments/E01-stentor-map/RESULTS.md) | FAIL (1 pass, 1 fail, 2 uninterpretable) |
| 6. E02-local-negative-image | [`experiments/E02-local-negative-image/RESULTS.md`](../experiments/E02-local-negative-image/RESULTS.md) | FAIL (2 of the discriminating predictions missed) |

## 1–3. The tape

- **Encoding is readable, recall is not.** Held-out encoding r 0.5–0.8. Recall r ≈ 0 at every delay and in every
  recall mode (cue, no cue, NM pulse, NM-driven excitability). No mechanism's ablation CI excludes zero, including
  frozen weights. A plain echo-state network beats it at encoding (0.730 against 0.535).
- **Rank order was reported as the positive, and it is weaker than it looked.** The dominant stream is recoverable
  from the rank position of cells: 77 % against a permutation 95th percentile of 57 %, 10/10 seeds. But rank is
  accumulated from each cell's excitatory conductance (feedforward + recurrent) **while the stimulus plays**, and the
  feedforward term dominates (8 nS against about 1 nS per recurrent spike). It is mostly a readout of which input
  fibres are active, not something the network keeps. No input-only control was run, and the permutation null
  shuffles 50 ms windows freely, breaking their autocorrelation; a circular-shift null would be stricter.
- **Recall delays are mislabelled.** Each recall probe's own duration is not counted before the next one
  (`recall/protocol.py`), so probe k starts `d_k + k × probe length` after encoding: 5 / 40 / 140 s on
  `quick.yaml` against the labelled 5 / 30 / 120 s (reported as 5 min / 30 min / 2 h after time compression). Recall
  is at chance at every delay, so no verdict changes; every delay axis is off by up to that amount.
- **The echo-state baseline had more units** (250 against the spiking readout's 200 E cells). That favours it; the
  encoding gap is partly a size effect.
- **The write is not stream-specific.** The weight change predicted from any of 20 never-played streams matches the
  real one as well as the played stream's does (stored stream ranked 1st in 0/10 seeds). Under the default rule the
  write is pure depression; under a calibrated rule it is pure potentiation. Neither is specific.
- **The neuron model is the binding constraint for storage.** Luboeinski & Tetzlaff's reference code reproduces
  its paper. neurotape's STC code recalls once the paper's LIF cell replaces the AdEx + T-current cell, and
  over-recalls with every difference removed. Nothing else of nine single changes moves it.

## 4–6. Habituation

**Spectral specificity.**
- Steps 1–2: short-term depression, a per-spike slow pool and a presynaptic long-term rule all generalise
  (recognition ≈ 0). Only the postsynaptically gated `hebb_only` rule recognises the stored sound. It does so at
  30 min, and keeps spectrum, not temporal order. That 30-min timescale is set by the Hebbian factor eroding in
  silence (it starts off its resting state), not by its 1 h recovery constant (REVIEW R1).
- E02, P1: depletion carries **no** specific retention above the 0.05 SESOI at any delay (2 s – 90 min) or overlap
  level. The least-overlapping probe is suppressed as much as the exposed sound (0.425 against 0.420 at 2 s).
- The cause is the periphery as much as the synapse. At 60 dB SPL, the least-overlapping of 20 random 4-band
  sounds still overlaps the exposed one at 0.59 (range 0.42–0.70) in the auditory nerve. No truly non-overlapping
  input exists in this model at that level.

**Learned inhibition (E02, Arm B).**
- Inhibitory STDP (Vogels et al. 2011 form) on a feedforward pathway learns a suppression of 0.17 at 5 min and
  0.13 at 30 min.
- Removing the pathway reverses 100 % of it, for every probe.
- The learning is only partly specific (A 0.17, least-overlapping 0.10), so removal is only partly specific.
  Removing the same pathway leaves the excitatory-depression arm unchanged. As a measurement, removal separates
  the two mechanisms.
- The preregistered criterion (reversal specificity ≥ half the learned component) failed. It asked removal to be
  more specific than the learning, which it cannot be.

**Stentor structure (E01 depletion cascade, E02 receptor pools).**
- E01: slowing recovery deepened the decrement, as the cascade predicts. It also moved the half-decrement point
  *later*, where Stentor shows faster habituation. The treatment-matched untrained control drained to the floor.
- E02: Rajan & Marshall's receptor-inactivation model, at their published rates (read per minute), under a full
  synthesis block:
  - untrained response −32 % at 20 min, −79 % at 90 min (massed); below spontaneous in the 2 h spaced schedule;
  - decrement deepened by 0.040 only;
  - retention prolonged by ≤ 0.014.
- In Rajan et al. 2026 the untrained, drug-treated cells kept their baseline. In Rajan & Marshall's own model,
  surface receptors degrade at a basal rate, so a block drains them too; a cell far above a hard contraction
  threshold keeps responding while its receptors drain. **The organism's result depends on that threshold. A graded
  readout, like this network's, exposes the drain.**

**Spacing.** In no mechanism here does spaced training beat massed at equal count (E02, P5). Spaced − massed
suppression at 5 min: R −0.07, B −0.04, A 0. H's −0.20 is confounded (its control erodes over the 2 h schedule;
REVIEW R1). Every mechanism modelled has one decay timescale, so early
blocks fade. Beck & Rankin 1997 (*C. elegans*) found the opposite for 24 h retention.

**Dishabituation.** No insert produced dishabituation in any arm (E01, SR3), matching Stentor. A strong insert
deepened the next response in `hebb_only` by 3.5 %.

## Cross-cutting findings about method

1. **The analytic efficacy model sets direction, not size.** Spikes are a thresholded function of efficacy:
   - small effects are compressed (E01 decrement 0.057 in spikes against 0.126 in efficacy; E02 block effect 0.040
     against 0.051);
   - large ones are expanded (E02 suppression at 2 s: 0.42 against 0.23).
2. **An angle between change vectors that share a baseline is not tested against 90°.** In E02 the trial-label null
   for the within- against across-session angle was 59–61° in every arm. Tsukano et al. 2026's 78.2° has no
   reported null.
3. **A fully paired design gives a plasticity-off arm zero variance.** Trained and control networks are then
   identical, and an MDE computed from them is 0 (E02 DEVIATIONS #1). Use per-criterion noise.
4. **Copies within one batch do not share noise.** Paired comparisons must be separate calls with the same seed.
5. **Release conventions diverged silently.** `spont_release()` and `fast_forward` use U = 1 with depression off,
   while `run()` releases U per spike. v0.1.0 results depend on the first convention and are self-consistent. New
   code (the receptor pools) must use the second.

## Open defects and loose ends

A pre-release review of the code and statistics is in [`docs/REVIEW.md`](REVIEW.md); the defects below are the
ones that remain unfixed.

- **model-v0.2.0 settle crash.** A plastic FF pathway that receives an FF spike during the 3 s settle, before α
  exists, crashes. It cost E02 its Arm B seed 0. Fix: use G × W_fe before α is set, as model-v0.2.1.
- **Recall-delay bookkeeping** (above): the fix changes every future tape timeline, so it waits for a model
  version that re-runs the tape experiments.
- **`input_plastic` + `freeze_plasticity_at_recall` would not build** (`network.py`: `pl_t` is added only to the
  E→E namespace). Never run; it raises.
- **Kit commit guard false positive.** `.agents/githooks/pre-commit` blocks any staged `experiments/*/PREREG.md`
  once its prereg tag exists, even when the file is unchanged. Merging `main` into an experiment branch therefore
  needs `--no-verify`. The fix belongs in the kit repo: compare the staged file with the tag's copy.
- The binaural front end and retrieval-as-writing (C1–C8) are built and not run. CoNNear playback has never run.
  Nothing above 200 E / 50 I has been run.
- No claim ID in `research/`. The simulation findings are recorded there as a simulation study
  (`projects/audio-evoked-potentials/simulations/runs/2026-09-24-sim-neural-memory-habituation.md`).

## If this is picked up again

- **Tape:** a larger network (800 E / 200 I) before any new mechanism; the held drives are in
  [`docs/DEFERRED.md`](DEFERRED.md).
- **Habituation:** E02 RESULTS §8. In order: fix the settle crash; add a hard output threshold as a switchable
  readout and test whether it alone rescues Stentor's untrained baseline; build a genuinely low-overlap stimulus
  pair; restate the removal criterion relative to learning specificity.
