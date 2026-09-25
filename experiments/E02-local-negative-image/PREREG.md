# E02-local-negative-image — where depletion stops carrying stimulus-specific retention, and whether a learned local negative image can be told from excitatory depression by removing it

Preregistered: 2026-09-24   Model tag: model-v0.2.0   Author: LLM session (Claude Opus 5.5) + Joshua Anderton
Attempt: 1   Replaces: — (E01-stentor-map is closed FAIL; E02 is a new question, not a retry)

**Read first.**
- The research behind this design, and every place it departs from the operator's prompt:
  [`docs/E02/RESEARCH.md`](../../docs/E02/RESEARCH.md).
- The pressure test: [`docs/E02/pressure-test.md`](../../docs/E02/pressure-test.md).
- **Results here are statements about these models. They are never evidence about mouse cortex, OFC, Stentor, or
  biology generally.**

**Protocol version.**
- This file follows the installed `.agents/protocols/PREREG_PROTOCOL.md` (kit `e64136a`, ten sections).
- It also adopts, voluntarily, the stricter additions in the kit's uncommitted draft protocol, each placed inside
  one of the ten sections:
  - an `Attempt:` header and an `EXPERIMENTS.md` registry;
  - estimands with their Monte-Carlo SE (§3);
  - prior knowledge and calibration (§8);
  - pilots on off-list seeds only (§8);
  - sensitivity runs for [ARBITRARY] parameters (§5, §6);
  - an unregistered-steps table (§8).

## 1. Question

**Primary.** In this network (Zilany AN → relay → two-pool depressing synapses → LIF E/I, plus a fixed feedforward
inhibitory pathway), up to which delay and at which input overlap does **synaptic depletion alone** (Arm A) carry
**stimulus-specific** retention above a smallest effect of interest?

**Secondary.** Two local learned mechanisms are compared: **learned inhibitory potentiation** (a negative image,
Arm B) and **postsynaptically gated excitatory depression** (Arm H). Does **removing the inhibitory pathway** after
training reverse B's suppression specifically, while leaving H's alone?

**Tertiary.** Does the Rajan & Marshall 2025 receptor-inactivation structure (Arm R) satisfy the Stentor
constraints under a synthesis block? The constraints are: faster decrement, longer retention, and an untrained
baseline that holds.

**Premise.**
- Arm A's failure region is the reportable finding.
- Arms B and H are sufficiency comparators, not the hypothesis.
- Arm R reproduces a published structure, not a mechanism claim.

## 2. Prediction(s) — risky, numeric, directional

Every prediction is labelled either **[DISCRIMINATING]**, which counts toward the verdict, or
**[POSITIVE CONTROL]**, which is guaranteed or near-guaranteed by construction, is reported, and cannot count. The
analytic numbers come from `predict.py` → `predictions/predictions.json`, which ran on the **off-list** seeds
900–909 before this tag, from the mean-field pools in `habituation/analytic.py`. They are **efficacy**
(fast × slow pool × surface receptors, weighted by each probe's footprint), not spikes.

### Stimulus overlaps (measured on the prediction seeds, not tuned)

Cosine overlap with the exposed sound A:

- **full** (A time-reversed): **0.9995**.
- **partial** (best spectral shift ≤ 1/3 octave): **0.82**, range 0.79–0.85.
- **none** (the lowest of 20 independent draws): **0.59**, range 0.42–0.70.

At 60 dB SPL any 4-component sound excites most AN channels. **A truly non-overlapping unexposed input does not
exist in this periphery.** "none" means *least overlapping achievable*. This is the first measured fact of E02,
and it constrains every specificity claim below.

**P1 — Arm A failure map [DISCRIMINATING, primary].**

- **Analytic prediction.** A's specific retention SR = S_A − S_B never exceeds the SESOI (0.05):
  - maximum **0.021** (none), **0.007** (partial) and **0.000** (full), all at 2 s after training;
  - below 0.003 by 30 s;
  - zero from 100 s onward.
- The same holds massed and spaced.
- A's *non-specific* suppression S_A is 0.23 at 2 s, 0.13 at 10 s, 0.03 at 30 s, and 0 from 100 s.
- **Predicted boundary: none**, for every probe and schedule. There is no delay at which depletion carries
  stimulus-specific retention above the SESOI.
- **Counts against:** a delay at which SR's 95 % CI lower bound exceeds 0.05 for any probe. The likeliest place is
  2–10 s on the none-probe, if the E cells' spike threshold amplifies the 0.021 efficacy difference by more than
  about 2.4×.
- **Risk.** This is the risky part. Spike suppression is a thresholded function of efficacy, and E01 found spikes
  and efficacy disagreeing by factors of 2–3. My credence that P1 passes is about **60 %**.

**P2 — B-vs-H removal [DISCRIMINATING].** Read at delays 300 s and 1800 s, both schedules. By 300 s depression has
recovered analytically (P1), so A contributes nothing there.

- **P2a — B has a learned component.**
  - Definition: LC = S_A(B) − S_A(A), paired by seed. Its 95 % CI lower bound should exceed 0.05.
  - Not analytic, because iSTDP is gated by spikes.
  - Direction: positive. Credence ~70 % at 300 s and ~55 % at 1800 s (G relaxes with τ = 1 h).
- **P2b — removal reverses B specifically.**
  - Measure: the trained-specific disinhibition of A minus that of the none-probe,
    `SRI = rev(A) − rev(none)`, where
    `rev(p) = [(tr_off − tr_on) − (ctl_off − ctl_on)] / ctl_on`.
  - Prediction: SRI ≥ ½·LC, i.e. the CI of SRI − ½·LC lies above 0.
  - **Counts against:** SRI below half the learned component.
  - **Risk:** "none" overlaps A at 0.59, so a spectral negative image also inhibits the none-probe. That shrinks
    SRI. Credence ~45 %.
- **P2c — H is untouched by removal.** SRI_H within ±0.05 (TOST).
  - This is **not** guaranteed: H carries the same fixed pathway, and removing it disinhibits a depressed and a
    naive input by different amounts.
  - **Counts against:** SRI_H outside the bound.
  - Credence ~70 %.

**P3 — naive removal is not stimulus-specific [DISCRIMINATING].**

- In the untrained (Z) control, removing the pathway changes A and the none-probe equally. The difference in their
  relative disinhibition should lie within ±0.05 (TOST).
- **Counts against:** a difference outside the bound. The trained SRI is a difference-in-differences, so this
  would not invalidate P2, but it would mean the pathway's naive coverage is stimulus-dependent.
- Credence ~70 %.

**P4 — Arm R under a synthesis block (×0 against ×1).** Analytic, efficacy.

- **P4a — the block deepens the decrement [DISCRIMINATING, massed only].**
  - Prediction: D rises from 0.244 to 0.295 (Δ = **+0.051**). The half-decrement point is **unchanged at
    presentation 26** on all ten prediction seeds.
  - Criterion: ΔD's 95 % CI lower bound > 0.05.
  - The predicted mean sits on the threshold, so credence is ~50 %.
  - Spaced ΔD (0.83) is **not** a test: it includes 2 h of baseline drain in the untrained direction. It is
    reported only.
- **P4b — the block prolongs retention by more than the SESOI at 20, 30, 60 and 90 min [DISCRIMINATING].**
  - Analytic ΔS_A (block − none): +0.015, +0.010, +0.010 and +0.011 (massed).
  - Prediction: **fails**; ΔS_A < 0.05 at every delay.
  - R&M's recycling (τ = 10 min on the per-minute reading) returns the receptors before 20 min.
  - **Counts against my prediction:** a 95 % CI lower bound above 0.05 at any retention delay.
- **P4c — the untrained baseline holds under the block [DISCRIMINATING; the Stentor constraint].**
  - Analytic untrained efficacy change (block vs no block), massed schedule: **−0.38 (20 min), −0.49 (30 min),
    −0.72 (60 min), −0.85 (90 min)**.
  - Prediction: **FAIL**, because the surface pool drains at R&M's basal degradation rate.
  - This is the pressure test's falsifier: the block must not drain the untrained baseline. **I predict that R&M's
    own structure, with their own rates, fails it** in a graded-output network. Stentor escapes it through a hard
    threshold.
  - **Counts against my prediction:** the untrained spike response staying within ±0.05. That would require the E
    cells to saturate strongly enough to hide a 38–85 % efficacy loss.
  - Credence in FAIL ~85 %.

**P5 — massed vs spaced (Beck & Rankin 1997).** A measurement; directions stated:

- **A:** no difference from 300 s on (both analytically zero). **[POSITIVE CONTROL]**
- **R:** massed > spaced. Analytic S_A at 300 s is 0.137 massed against 0.060 spaced, so R shows the **opposite**
  of the spacing effect. This is DISCRIMINATING as a direction: spaced ≥ massed would count against it.
- **H:** massed ≥ spaced at 300–3600 s. L decays with τ = 1 h, so early blocks fade. Opposite of the spacing effect.
- **B:** massed ≈ spaced. iSTDP is homeostatic, so each block re-saturates. Low confidence (~50 %).
- Beck & Rankin's C. elegans pattern (spaced > massed for long-term retention) is therefore predicted to appear in
  **no** arm. Finding it in any arm counts against this prediction.

**P6 — global-gain positive control [POSITIVE CONTROL].**

- Arm G steps the relay→E gain down (1.0 → 0.9 → 0.8) across training.
- Its suppression of A exceeds 0.05 (P6a), and its specific retention is within ±0.05 (P6b).
- If P6b fails, the specificity readout cannot tell global gain from specific suppression, and **every specificity
  result in this experiment is reported as uninformative**.

**Axis readout (measurement, no criterion).**

- Measured: the angle between the within-session change vector (block 1: last 5 − first 5 trials) and the
  across-session change vector (block 3 first 5 − block 1 first 5).
- It is computed over E cells, in the onset (0–0.2 s) and sustained (1.0–1.5 s) windows, per arm, spaced schedule.
- Each angle is reported against a per-seed **trial-label permutation null** (1000 permutations). No analytic
  expectation is derived, so it is not a criterion.
- It is read only if P6 passes.

## 3. Pass / fail criteria (numbers written before any output is seen)

**Estimand.** The paired mean over the 20 seeds. Each seed is one network and one stimulus family, with the trained
and control networks sharing relay rasters and noise seeds. The Monte-Carlo SE of each estimate is its across-seed
SE, reported beside it.

**Suppression.**
- S_p = 1 − R_trained(p) / R_control(p).
- R is the E spikes during the 1.5 s probe minus the expected spontaneous count.
- Control = a naive network carried through the same elapsed time under the same manipulations (same synthesis
  block; gain 1.0).
- SR_p = S_A − S_p.

**SESOI and bounds.**
- **SESOI = 0.05** (5 % of the control response) [ARBITRARY; also E01's order of effect].
- TOST bounds: ±0.05 at α = 0.05, i.e. the 90 % CI must lie inside ±0.05.

**MDE.**
- Computed per cell from the plasticity-off arm Z, which runs first:
  `(t_{0.975,19} + t_{0.80,19}) · sd / √20 ≈ 0.66 · sd`.
- The design MDE is the **largest** of those cells.

**Verdict rules** (implemented in `analyse.py`):

| Rule | PASS | FAIL | otherwise |
|---|---|---|---|
| *exceeds X* | 95 % CI lower bound > X | 90 % CI inside ±SESOI **and** MDE ≤ SESOI | UNINTERPRETABLE |
| *within* (TOST) | 90 % CI inside ±SESOI | whole 95 % CI outside ±SESOI | UNINTERPRETABLE |

**An effect under the MDE is UNINTERPRETABLE, never FAIL.**

| Criterion | Metric | Pass | Fail | Pre-registered value / derivation |
|---|---|---|---|---|
| P1 A-map (massed, spaced × full, partial, none) | largest delay with SR 95 % CI lo > 0.05 | equals predicted boundary (both "none", or within one delay step) | otherwise | predicted boundary **none** for all 6 cells (max efficacy SR 0.021) |
| P2a learned component (×2 schedules × 300, 1800 s) | LC = S_A(B) − S_A(A) | exceeds 0.05 | rule | not analytic; direction + |
| P2b B removal reverses (same cells) | SRI_B − ½·LC | exceeds 0 | rule; UNINTERPRETABLE if P2a is not PASS | not analytic |
| P2c H removal null (same cells) | SRI_H | within ±0.05 | rule | not analytic; 0 |
| P3 naive removal unspecific (×2 schedules) | rev(A) − rev(none) in Z at 2 s | within ±0.05 | rule | 0 |
| P4a block deepens decrement (massed) | ΔD (syn0 − syn1), first_k = 2, last_k = 4 | exceeds 0.05 | rule | **+0.051** |
| P4b block prolongs retention (×2 schedules × 1200, 1800, 3600, 5400 s) | ΔS_A (syn0 − syn1) | exceeds 0.05 | rule | massed +0.015/+0.010/+0.010/+0.011; spaced +0.014/+0.012/+0.013/+0.014 |
| P4c untrained baseline holds (same cells) | R_ctl(syn0)/R_ctl(syn1) − 1 | within ±0.05 | rule | efficacy massed −0.38/−0.49/−0.72/−0.85; spaced −0.95 to −0.99 |
| P6a gain suppresses (×2 schedules, 300 s) | S_A in G | exceeds 0.05 | rule | ≥ 0.2 expected by construction (gain 0.8) |
| P6b gain unspecific (same) | SR_none in G | within ±0.05 | rule | 0 by construction |

**Verdicts.**
- **E02 is PASS if every DISCRIMINATING criterion matches its predicted outcome.** Where the prediction is a
  failure (P4b, P4c), "matches" means the criterion comes out FAIL.
- E02 is FAIL if any comes out opposite to its prediction.
- It is UNINTERPRETABLE where the deciding criteria are UNINTERPRETABLE.
- P5 and the axis readout are measurements and are reported against their stated directions.

The analytic code that produced the predicted values is committed: `predict.py`, `habituation/analytic.py`
(model-v0.2.0) and `predictions/predictions.json`.

## 4. Falsifiers

These close this line of work, as opposed to failing one criterion:

- **P1 fails in the specific direction.** A carries specific retention above the SESOI at ≥ 300 s. Then the
  premise that depletion generalises is wrong in this model, and any local-memory mechanism (B, H) is unnecessary
  for specificity at these overlaps.
- **P6b fails.** The specificity readout cannot tell global from specific, so no specificity claim from these
  networks is admissible until the readout is redesigned.
- **P2b and P2c both fail in the same direction:** removal changes B and H alike. Removal then cannot discriminate
  these mechanisms, and the in-silico-muscimol design should be abandoned for this network.
- **P4c passes against the prediction.** The analytic efficacy model is then a poor guide to spikes by a large
  margin, and every efficacy-derived prediction in this repo (E01, E02) needs re-deriving through the network.

## 5. Model specification

**Base.**
- `neurotape.habituation`, **model-v0.2.0**. The equations, and every pre-existing parameter with its source, are in
  `ASSUMPTIONS.md` § "Minimal habituation model" and `habituation/config.py`.
- Base config: `configs/habituation.yaml`: Zilany, Bruce & Carney 2014 AN via `cochlea` [LIT: 10.1121/1.4837815];
  32 CFs, 125 Hz–7 kHz; 60 dB SPL.
- Relay: 8 units per CF.
- Network: 200 E and 50 I LIF cells; 0.5 ms step.
- Two-pool depression: U 0.5, τ_fast 0.8 s, a_slow 0.05, τ_slow 20 s, as in E01.

**New in v0.2.0**, all defaults off, all switched on here only through `config.yaml`:

| Parameter | Value | Tag |
|---|---|---|
| FF population | 50 LIF cells, tonotopic (σ 0.3 oct), I-cell membrane | [ARBITRARY] — same form as the existing I cells |
| relay→FF peak w_rf | 0.6 nS, no short-term depression | [ARBITRARY] — operating point, §8 |
| FF→E peak w_fe | 0.3 nS × G | [ARBITRARY] — operating point, §8; sensitivity ×0.5, ×2 |
| G resting / initial (g0) | 1.0 (non-zero, so removal "before training" is a manipulation) | [ARBITRARY] |
| iSTDP rule | pre spike: G += η(x_post − α); post spike: G += η x_pre; traces τ 20 ms, +1 per spike | [LIT: 10.1126/science.1211095, AB-only; equation from BG] |
| α | 2 ρ0 τ_stdp, ρ0 = measured spontaneous E rate | [DERIVED; Vogels' form] |
| η (Arm B) | 0.015 | [ARBITRARY] — engagement criterion, §8; sensitivity ×0.5, ×2 |
| G relaxation τ | 3600 s | [DERIVED — matched to H's τ_s] |
| G_max | 20 | [ARBITRARY]; never approached in pilots |
| Receptor pools (Arm R) | dS/dt = k_syn − k_deg S + k_rec I; dI/dt = −(k_rec + k_deg + k_des) I; on release: k_int·rel·S from S to I; efficacy × S, per relay fibre | [LIT: 10.1016/j.cub.2025.05.071, FT] — their eq. 2 sign read as +k_deg |
| k_rec, k_deg, k_des | 0.1, 0.02, 0.005 per minute | [LIT, same] — **per-minute reading assumed** (stimuli were one per minute; no unit given) |
| k_syn | solves S = 1 at spontaneous release, ×synthesis_scale | [DERIVED] |
| k_int | 2e-4 per unit release (≈ 2 % of surface per 1.5 s presentation on a driven channel) | [ARBITRARY] — order of R&M's k_int × P_open; sensitivity ×0.5, ×2 |
| Removal | FF→E output × 0 at probe time (`State.ff_out`) | switch |
| Global gain | relay→E × g_in (`State.g_in`) | switch |

A pass that depends on an [ARBITRARY] value is not robust. The sensitivity runs (§6) test η, w_fe (in B and H) and
k_int (in R, under the block). A headline criterion whose point estimate crosses its threshold anywhere in those
ranges is reported as **not robust**.

## 6. Design

**Arms** (every arm carries the FF pathway at g0; salience off):

| Arm | What it is |
|---|---|
| A | depression on |
| H | depression off; Hebbian L, η_hebb 0.0125, τ 1 h |
| B | A + plastic G |
| R | depression off; receptor pools; synthesis ×1, ×0.25, ×0 from network build (3 s before training), in trained and control alike |
| Z | plasticity off; the MDE control |
| G | Z with relay→E gain 1.0 / 0.9 / 0.8 from presentations 1 / 21 / 41, held to the probe |

**Schedules.** Equal count (60 presentations of A, 1.5 s each, 3 s onset to onset):
- **massed:** 60 in a row;
- **spaced:** 3 blocks of 20, with 1 h between blocks, fast-forwarded (Beck & Rankin 1997 structure).

**Probes.**
- After training, at each delay in **2, 10, 30, 100, 300, 1200, 1800, 3600 and 5400 s**, a copy of the trained
  network and a copy of the time-matched control each hear **A, full, partial and none**.
- Each probe is heard with the FF pathway **intact** and **removed**, in separate calls with the same noise seed,
  so they are paired.
- Copies within one batch draw different noise and are therefore never compared with one another.

**Seeds.**
- 0–19, fixed. Each seed is one network and one stimulus family.
- N = 20 per arm × variant × schedule.
- Prediction seeds 900–909 were used only by `predict.py` and the pilot.

**Controls.**
- Z runs first and fixes the MDE.
- G is the readout's positive control.
- Every probe has its time-matched naive control.
- R's untrained baseline is compared paired across synthesis levels.

**Sensitivity.** Seeds 0–4, both schedules:

| Arm | Varied parameters |
|---|---|
| B | η ×0.5, ×2; w_fe ×0.5, ×2 |
| H | w_fe ×0.5, ×2 |
| R (block × 0) | k_int ×0.5, ×2 |

This is 80 jobs. With 5 seeds only the **direction** of the point estimate is read.

**Runs and exclusions.**

| Stage | Jobs |
|---|---|
| stimuli | 20 |
| control (Z) | 40 |
| main (A, H, B, R×3, G) | 280 |
| sensitivity | 80 |

- A failed job is kept in `runs.json` with its error, listed in RESULTS, and excluded from means. It is **never
  re-run silently**; a re-run is a deviation.
- A probe whose control response ≤ 0 gives NaN for that seed. The count is reported.
- A seed whose partial overlap falls outside the report-only band [0.7, 0.9] is kept and flagged.

**Analysis window.** The whole 1.5 s probe for S. Onset (0–0.2 s) and sustained (1.0–1.5 s) windows are recorded
for every probe and for the axis readout.

## 7. Environment

| Item | Value |
|---|---|
| Language | CPython 3.11.16 (uv), macOS 26.5 arm64 |
| `ENV.lock` sha256 | `97948c058cc35a2f96564e7bc639c2206d4cc9ba880e663232f38fa6d9b5db0c` (package set identical to E01's; only the header changed) |
| Execution | pure numpy (`neurotape.habituation`), one BLAS thread per process (set in `run.py`), 8 spawn workers; Brian2 unused |
| cochlea | git `b51ffde2`, GPL-3 |
| Code | `src/` must equal `model-v0.2.0` (`run.py` refuses otherwise) |
| Reproduction tolerance | every `runs.json` byte-identical on re-run on this machine; other platforms: not claimed |

## 8. Adaptive stages (optional) — and prior knowledge, calibration, unregistered steps

**Stages.**
- The order is fixed: `stimuli` → `control` → `main` → `sensitivity`. `run.py` refuses `main` before `control`
  exists.
- There are **no adaptive revisions planned**. Any change goes through `DEVIATIONS.md`, and before a dependent run
  through an `-interim-N` tag.

**Prior knowledge** (what the author knew before writing this):
- E01's results: `std` depletion deepens when its recovery slows, and controls drain when recovery is frozen.
- Steps 1–2: depletion generalises; `hebb_only` is specific and lasting.
- All the sources in `docs/E02/RESEARCH.md`.
- No E02 output for any on-list seed has been seen.

**Calibration and pilots before this tag** (all on off-list seeds 901–902 / 900–909; none is evidence):

| # | Step | Seeds | What was seen | What it set |
|---|---|---|---|---|
| U1 | FF operating point: scan w_rf × w_fe, naive response only | 901–902 | at 4 / 1 nS the FF cells fired 200–280 Hz and cut the naive E response 91–96 %; at 0.6 / 0.3 nS, ~27 Hz and ~25 % | w_rf 0.6, w_fe 0.3 (target stated before the scan: FF 20–60 Hz, 20–35 % naive cut) |
| U2 | iSTDP engagement: G after 20 presentations, synaptic variable only | 901–902 | top-decile G 1.15 / 1.37 / 1.69 at η 0.002 / 0.005 / 0.01; **1.98 at η 0.015** | η 0.015 (criterion: top-decile G ≈ 2 g0) |
| U3 | A mistaken diagnosis of "iSTDP drift in silence" | 901–902 | the drift was G's own relaxation to g0; FF cells are silent at rest | reverted to Vogels' α; no model change survived |
| U4 | Receptor check: steady state and fast-forward vs direct | 901 | found two release-convention bugs (derivation and fast-forward used U = 1 with depression off); fixed; direct and fast-forward now agree to 0.003 | model code, before the tag |
| U5 | `predict.py` on seeds 900–909 | 900–909 | the analytic numbers in §2–3; a "none" ceiling of 0.1 was unreachable (32 min of draws) | none = lowest of 20 draws; partial band made report-only [0.7, 0.9] |
| U6 | Smoke test of `run.py` on seed 900, every arm and variant | 900 | run status and returned fields only; outcome values **not printed** (`exploratory/pilot/smoke.py`) | no change, unless it crashed |

## 9. Open decisions

Every choice the prompt left open, decided here before any on-list run:

1. **Overlap metric.** Cosine of the driven relay profiles (mean rate above spontaneous, per CF). This is
   `analytic.overlap`.
2. **Overlap levels.**
   - full = A time-reversed;
   - partial = the shift in {1/12, 1/8, 1/6, 1/4, 1/3} octave whose overlap is closest to 0.5;
   - none = the lowest-overlap of 20 independent draws.
   - The prompt's targets (partial ≈ 0.5, none ≈ 0) are **unreachable** in this periphery at 60 dB (U5). The levels
     achieved on the prediction seeds are ≈1.00 / 0.82 / 0.59.
3. **Drive matching.** B's level is secant-matched so its driven relay sum is within 5 % of A's (≤ 4 steps). The
   residual mismatch is reported per seed.
4. **Delays.** 2, 10, 30, 100 and 300 s, plus the Stentor-relevant 1200, 1800, 3600 and 5400 s.
5. **Sessions.** Massed 1 × 60; spaced 3 × 20 with 1 h rests. The word used is "session", never "day".
6. **Removal reference probe.** "none" (least overlapping). full is useless for specificity, because it shares A's
   spectrum.
7. **Initial weight.** g0 = 1.0 × w_fe = 0.3 nS; it cuts the naive response ~25 % (U1).
8. **Windows.** Onset 0–0.2 s; sustained 1.0–1.5 s; score 0–1.5 s.
9. **Gain control.** Steps at presentations 1, 21 and 41 in both schedules, held through the delay.
10. **first_k = 2, last_k = 4, SESOI = 0.05, α = 0.05, power 0.80.**
11. **Restatements of the prompt** (reasons in `docs/E02/RESEARCH.md` §3–4):
    - B-naive removal is a *specificity* criterion (P3). Otherwise it fails by construction.
    - The FF pathway is present in every arm, so H's removal test is not zero by construction.
    - R has depression off.
12. **R's block onset** is network build, 3 s before training, in trained and control alike.

## 10. Timestamp / archive

- The `E02-local-negative-image-prereg` tag is made with `.agents/tools/tag`. Its receipt is posted to the
  experiment PR, which carries GitHub's server timestamp.
- **No Zenodo, SWHID or RFC 3161 receipt.** Local git dates plus the PR receipt are all there is.
