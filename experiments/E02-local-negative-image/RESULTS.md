# E02-local-negative-image — Results

| Item | Value |
|---|---|
| Run tag | E02-local-negative-image-run |
| Model tag | model-v0.2.0 |
| ENV.lock sha256 | 97948c058cc35a2f96564e7bc639c2206d4cc9ba880e663232f38fa6d9b5db0c |
| Prereg tag | E02-local-negative-image-prereg → 8e185cf |
| Runs | 20 stimuli + 40 control + 280 main + 80 sensitivity = **420 jobs; 10 failed** |

**Every failed job is Arm B, seed 0**: 2 main (massed, spaced) and 8 sensitivity. They are kept in `runs.json`,
excluded from means and not re-run.

**The failures are a model bug** (DEVIATIONS #2):

- During the 3 s settle, before α exists, a plastic B network routed FF spikes to a fixed-weight matrix that is
  `None` for plastic configs.
- It crashes only if an FF cell fires during settle. That happened on seed 0 and on no other seed (including pilot
  seed 900).
- B's comparisons therefore use 19 seeds.

**These results are statements about these models, never evidence about mouse cortex, OFC, Stentor, or biology.**

## 1. Criteria table

All numbers are spike-based suppression. Verdicts come from `analyse.py`, exactly as frozen. "Pred." is the outcome
PREREG §2–3 predicted; "own MDE" is DEVIATIONS #1.

| Criterion | Pre-registered threshold | Predicted (value; outcome) | Observed mean [95 % CI] | own MDE | Verdict | Matches prediction? |
|---|---|---|---|---|---|---|
| P1 A-map, 6 cells (massed/spaced × full/partial/none) | boundary = predicted | none; PASS | boundary **none** in all 6 | — | **PASS** ×6 | yes |
| P2a learned component, massed 300 s | CI lo > 0.05 | +; PASS | +0.171 [+0.145, +0.197] | 0.037 | PASS | yes |
| P2a massed 1800 s | CI lo > 0.05 | +; PASS | +0.134 [+0.115, +0.154] | 0.027 | PASS | yes |
| P2a spaced 300 s | CI lo > 0.05 | +; PASS | +0.129 [+0.108, +0.151] | 0.030 | PASS | yes |
| P2a spaced 1800 s | CI lo > 0.05 | +; PASS | +0.085 [+0.071, +0.099] | 0.020 | PASS | yes |
| P2b B removal reverses specifically (SRI − ½LC), massed 300 s | CI lo > 0 | ≥ 0; PASS | −0.019 [−0.043, +0.006] | 0.035 | **FAIL** | **no** |
| P2b massed 1800 s | CI lo > 0 | PASS | −0.009 [−0.024, +0.007] | 0.022 | **FAIL** | **no** |
| P2b spaced 300 s | CI lo > 0 | PASS | −0.001 [−0.018, +0.015] | 0.023 | **FAIL** | **no** |
| P2b spaced 1800 s | CI lo > 0 | PASS | −0.002 [−0.019, +0.014] | 0.023 | **FAIL** | **no** |
| P2c H removal null, massed 300 / 1800 s | 90 % CI in ±0.05 | 0; PASS | +0.002 / +0.004 | 0.008 / 0.016 | PASS / PASS | yes |
| P2c spaced 300 / 1800 s | 90 % CI in ±0.05 | 0; PASS | +0.001 / −0.010 | 0.023 / 0.018 | PASS / PASS | yes |
| P3 naive removal unspecific (massed; spaced identical) | 90 % CI in ±0.05 | 0; PASS | −0.002 [−0.004, +0.001] | 0.004 | PASS | yes |
| P4a block deepens decrement, massed | CI lo > 0.05 | +0.051; PASS (marginal, ~50 %) | +0.040 [+0.038, +0.041] | 0.002 | **FAIL** | **no** |
| P4b block prolongs retention, massed 1200 / 1800 / 3600 / 5400 s | CI lo > 0.05 | +0.015/+0.010/+0.010/+0.011; FAIL | +0.007 / +0.006 / +0.003 / +0.014 | ≤ 0.014 | FAIL ×4 | yes |
| P4b spaced, 4 delays | CI lo > 0.05 | ~+0.013; FAIL | undefined (n = 0; see note) | — | UNINTERPRETABLE ×4 | — |
| P4c untrained baseline holds, massed 1200 / 1800 / 3600 / 5400 s | 90 % CI in ±0.05 | −0.38/−0.49/−0.72/−0.85; FAIL | **−0.320 / −0.417 / −0.634 / −0.792** | ≤ 0.006 | FAIL ×4 | yes |
| P4c spaced, 4 delays | 90 % CI in ±0.05 | −0.95…−0.99; FAIL | **−1.02 / −1.07 / −1.11 / −1.11** | ≤ 0.007 | FAIL ×4 | yes |
| P6a gain suppresses (positive control), both schedules | CI lo > 0.05 | ≥ 0.2; PASS | +0.173 [+0.170, +0.175] | 0.004 | PASS | yes (value below the "≥ 0.2" guess) |
| P6b gain unspecific (positive control), both schedules | 90 % CI in ±0.05 | 0; PASS | −0.002 [−0.006, +0.001] | 0.005 | PASS | yes |

**Notes on the table.**

- **P4b spaced.** With synthesis blocked for the whole ~2 h spaced schedule, the untrained control's driven response
  falls **below its spontaneous count** by 30 min. The response is ≤ 0 in all 20 seeds, so the suppression ratio is
  undefined at every retention delay. P4c spaced values below −1 mean the same thing. The analytic prediction
  (−0.95 to −0.99 in efficacy) forecast the drain; that it would take the *spike* response below zero, and so
  undefine P4b, was not foreseen.
- **P1** holds robustly. Spike suppression amplifies efficacy (S_A at 2 s is **0.42** in spikes against 0.23
  predicted in efficacy). Yet specific retention is **≤ 0** at every delay: the least-overlapping probe is suppressed
  *at least as much* as A (S_none 0.425 against S_A 0.420 at 2 s, massed). Depletion's generalisation is complete.

## 2. Verdict

**FAIL.** Under PREREG §3's rule, E02 passes only if every DISCRIMINATING criterion matches its predicted outcome.

**Two did not match:**

- **P2b** (four cells) fails, and not because removal failed.
  - Removing the pathway reverses **all** of B's learned suppression, for every probe. At 300 s massed:
    rev(A) = +0.171 = S_A, and rev(none) = +0.104 = S_none.
  - The learning itself is only partly specific. The least-overlapping probe still overlaps A at 0.59, so it is
    suppressed at 0.10 against A's 0.17.
  - So the specific part of the reversal (SRI = +0.067 [+0.036, +0.098]) is below the criterion's ½·LC = 0.085.
  - The criterion required removal to be *more* specific than the learning it removes, which a pathway removal cannot
    be. That is a flaw in how I wrote the criterion. It does not convert to a pass.
- **P4a** fails narrowly and cleanly.
  - The block deepens the massed decrement by **+0.040** (tight CI) against the 0.05 threshold. The analytic
    efficacy value was +0.051, which I flagged as sitting on the threshold.
  - The spike response deepens *less* than efficacy here, while at 2 s after training (P1) spikes amplify.

**What did match:**

- Every other discriminating prediction: P1 (all six cells), P2a, P2c, P3, P4b massed and P4c.
- **Both headline negative predictions held:**
  - depletion carries no specific retention above the SESOI at any delay or overlap;
  - Rajan & Marshall's receptor structure, with their rates, **drains the untrained baseline under a synthesis
    block** (−32 % at 20 min to −79 % at 90 min, massed) and does not prolong retention.

## 3. Patterns the model FAILED to reproduce

- **Stentor's untrained baseline under a protein-synthesis block** (Rajan et al. 2026): it drains, to below
  spontaneous in the spaced schedule.
- **Stentor's accelerated habituation under the block:**
  - the decrement deepens by 0.040 only (< SESOI);
  - the half-decrement point does **not** move earlier (massed: 0.8 presentations *later*, CI [−1.65, +0.05]).
- **Stentor's prolonged retention at 20–90 min:** ≤ 0.014.
- **The spacing effect (Beck & Rankin 1997, *C. elegans*):** spaced training beats massed in **no arm**.
  Spaced − massed suppression at 300 s: H −0.20, R −0.07, B −0.04, A 0.
- **Stimulus-specific retention from depletion** (the prompt's premise that depletion carries some specificity at
  low overlap): none, because no low-overlap stimulus exists in this periphery at 60 dB.
- **A truly unexposed input.** The least-overlapping of 20 draws overlaps A at 0.59 on average. Every specificity
  result here is bounded by this.

## 4. Sensitivity

Seeds 0–4. B's seed 0 failed, so B has n = 4. Only the direction of the point estimate is read.

| Varied | Result | Reading |
|---|---|---|
| B η ×0.5, ×2; w_fe ×0.5, ×2 | removal SRI stays positive: +0.062, +0.108, +0.092, +0.083 massed; +0.020 … +0.089 spaced | Direction robust. P2b's comparison to ½LC was not computed on the sensitivity runs (`analyse.py` records SRI only), so **P2b's robustness is unassessed**. |
| H w_fe ×0.5, ×2 | SRI −0.023 … +0.020 | Within ±0.05 everywhere, so **P2c is robust**. |
| R k_int ×0.5, ×2 under the block | massed retention at 5400 s +0.010 / +0.011 | Below 0.05, so **P4b massed is robust**. Spaced is undefined, as in the main run. |

No headline verdict's point estimate crosses its threshold in the ranges tested.

## 5. Controls

- **Z** (plasticity off): trained and control networks are **identical**, so every paired difference is exactly 0.
  The preregistered design MDE is therefore **0**, which is degenerate (DEVIATIONS #1).
- **G** (global gain → 0.8, the readout's positive control):
  - S_A +0.173, and specificity −0.002: global suppression reads as global.
  - The specificity readout is therefore **informative**, so the P1/P2 specificity results stand.
- **Naive removal** (P3): removing the pathway raises the naive response to A by +1.4 % and affects A and the
  none-probe equally.
- **Untrained-block baseline** (P4c): run before R's retention was interpreted. It drained, which is the reason P4b
  spaced is undefined.

## 6. Exploratory (clearly labelled)

**Axis readout.**

- The prereg made it a measurement, spaced schedule only, readable because P6 passed.
- **Chance is ~60°, not 90°.** Both change vectors subtract the same block-1 baseline, so they share a term. The
  trial-label null median is **59–61°** in every arm. An angle has to be read against that null, not against
  orthogonality. That is the same point the pressure test made about Tsukano et al.'s 78.2°.

| Arm | onset | sustained |
|---|---|---|
| H | **35.7°** | **39.9°** |
| R (block ×0) | 51.3° | 48.1° |
| R (block ×0.25) | 50.7° | 46.0° |
| B | 59.9° | 57.4° |
| A | 61.0° | 59.6° |
| Z | 59.2° | 54.7° |
| R (no block) | 65.8° | 62.8° |
| G | **70.0°** | **72.7°** |

- H is well below its null (its within- and across-session changes point the same way); G sits above it.
- Per-seed permutation tests at 2.5 % flag almost nothing (0–1 of 20 per arm). The across-seed means separate while
  the single-seed tests do not.

**Other measurements.**

- **Removal specificity when it is real (B):** SRI +0.067 (massed 300 s), +0.058 (massed 1800 s), +0.064 (spaced
  300 s), +0.040 (spaced 1800 s), all with CIs above 0.
- H's SRI is ≈ 0 everywhere. So **removal does discriminate B from H**, as a measurement, even though P2b as written
  fails.
- **B's learned weight:** mean G over connected synapses peaks at 1.56 (massed) and relaxes to 1.12 by 90 min.

## 7. What only worked because it was tuned

- **B's learned component (P2a) depends on η = 0.015**, chosen by an engagement criterion on the synaptic variable
  (PREREG §8, U2). Sensitivity shows the removal effect keeps its sign from η ×0.5 to ×2, but its size scales with η.
- **The FF operating point** (w_rf 0.6, w_fe 0.3) was set against a stated target before any scored run (U1).
  Nothing in P2c/P3 depends on it, per sensitivity.
- **Nothing else.** P1, P4 and P6 use v0.1.0 parameters, R&M's published rates, and a k_int whose ×0.5–×2 range
  leaves P4b unchanged.

## 8. Next EID

E02 is closed. A follow-up would be a new experiment, and would change:

1. **Fix the settle crash first**, as model-v0.2.1 on a `model/` branch: use G × W_fe before α exists. It must be
   bit-identical for every run that never hit the crash path.
2. **Restate P2b** as the specificity of reversal relative to the specificity of learning:
   `SRI / (S_A − S_none)` ≥ a threshold. Removal cannot be more specific than what it removes.
3. **Replace Z's MDE** with a noise source that exists: per-criterion MDE, or a Z arm whose control gets an
   independent noise seed.
4. **Get a genuinely low-overlap unexposed input** (a lower presentation level, narrower bands, or a single-band
   stimulus pair) before asking any specificity question of depletion again.
5. **For Stentor:** add the hard output threshold that R&M's model relies on, as a switchable readout, and test
   whether it alone rescues the untrained baseline under the block.

## Post-close review — 2026-09-25

An independent review of the analysis (docs/REVIEW.md) found four things. Nothing above is edited; these notes
qualify it.

1. **The MDE rule has two readings, and the literal one changes six cells** (DEVIATIONS #3). PREREG §3 says "an
   effect under the MDE is UNINTERPRETABLE, never FAIL"; `analyse.py` implements the narrower "FAIL needs
   MDE ≤ SESOI". With each criterion's own MDE and the literal reading, **P2b becomes UNINTERPRETABLE in all four
   cells** (means −0.019…−0.001 against MDEs 0.022–0.035) and **P4b massed at 3600 s and 5400 s become
   UNINTERPRETABLE** (0.003 vs 0.009; 0.014 vs 0.014). **The overall FAIL stands on P4a** (+0.040 against an MDE of
   0.002), which is FAIL under either reading.
2. **"No specific retention at any delay or overlap" (§1) is per cell, uncorrected.** Across the 54 map cells the
   largest 95 % upper bound is 0.043; with a Bonferroni correction it is 0.066, above the SESOI. The simultaneous
   statement is weaker than §1 reads.
3. **§4's last sentence over-reaches.** P2b's robustness was not assessed on the sensitivity runs (n = 4), so "no
   headline verdict's point estimate crosses its threshold" applies to P2c and P4b massed only.
4. **"Removal separates B from H" (§6) was inferred from two separate CIs**, B's excluding 0 and H's including it,
   not from a B − H contrast. The CIs do not overlap, but no paired B − H test was run.
5. **Arm H's spaced − massed difference (−0.20) is confounded** (docs/REVIEW.md, R1). H's Hebbian factor starts at
   1 and erodes in silence, so its control after the 2 h spaced schedule is far weaker (control response to A 989
   spikes at 2 s, against 2106 massed). B's and R's comparisons start from their true steady states and stand;
   "spaced training beats massed in no arm" rests on B and R.
6. **Arm R, spaced: "the driven response falls below its spontaneous count"** comes from subtracting the naive
   network's spontaneous count. The blocked control went nearly silent (about 4 spikes in 1.5 s), and that
   subtraction is what makes P4b-spaced undefined. P4c is FAIL on total counts too (−0.72 at 5400 s, massed).
