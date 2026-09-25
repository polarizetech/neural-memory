# E03-synthesis-block — can a minimal change to the Stentor receptor-inactivation model reproduce what a protein-synthesis block does to habituation?

Preregistered: 2026-09-25   Model tag: model-v0.4.0   Author: LLM session (Claude Opus 5.5) + Joshua Anderton
Attempt: 2 of the question "does Rajan & Marshall's receptor structure hold Stentor's synthesis-block results?"
(replaces E02-local-negative-image's tertiary question, which failed the untrained baseline in a graded network)

**Read first.**
- Model: `src/neurotape/singlecell/` (Rajan & Marshall 2025 in libRoadRunner, reproduction gate R1–R8; switches in
  model-v0.3.0 and model-v0.4.0, all defaulting to the published model). `ASSUMPTIONS.md` § "Single-cell Stentor".
- **Results here are statements about these models. They are not evidence about Stentor.** The targets are the
  published observations of Rajan et al. 2026; the model is judged against them.

## 1. Question

In Rajan & Marshall 2025's single-cell receptor-inactivation model, with the paper's own hard contraction threshold,
does any arm of a 16-arm factorial of minimal changes reproduce the **five** synthesis-block observations of Rajan et
al. 2026 while still passing the published model's own eight behaviours (R1–R8)? The changes are:

- recycling constitutive vs dependent on a labile, synthesis-dependent factor;
- internalisation vs Wood's in-place gating;
- basal turnover ×1, ×0.1, ×0.01, ×0.001.

**Hypothesis under test (the author's):** no arm does. The published structure makes one change do two jobs: the
block sets both the **rate** of habituation and the **floor** it reaches. Rajan 2026 report a faster approach to
**the same** floor.

## 2. Predictions — risky, numeric, directional

Each prediction is labelled either **[DISCRIMINATING]**, which counts toward the verdict, or **[POSITIVE CONTROL]**,
which holds by construction or by closed form, is reported, and cannot count. Numbers marked *closed form* come from
the untrained solution S(t) = 35·e^(−k_deg·s·t) (I = 0, so the labile factor cannot act) and the Poisson threshold.
They were computed before this tag **without running any protocol through the simulator**. Every other number is a
hand estimate from steady-state balance: surface loss per tap = 0.1·P_act·S, balanced by k_rec·X·I.

**P1 — the untrained baseline selects the turnover [POSITIVE CONTROL; closed form].**

Untrained p_block − p_control at level 4 (F = 1.5):

| k_deg scale | 180 min | 720 min | 810 min |
|---|---|---|---|
| 1 | −0.89 | −0.89 | −0.89 |
| 0.1 | −0.44 | −0.89 | −0.89 |
| 0.01 | −0.03 | −0.14 | −0.17 |
| 0.001 | −0.00 | −0.01 | −0.01 |

- At level 3 (F = 1.0), 180 min: −0.72, −0.48, −0.05 and −0.01 respectively.
- So **C1 passes only at ×0.001**, in all four recycling × mechanism combinations. The published model (×1) gives a
  contraction probability of 0.000 after 3 h of block against 0.72–0.89 untrained. That is **the Stentor
  constraint failed with the paper's own hard threshold**; E02 had shown it only with a graded readout.
- Not risky: arithmetic. Reported so no one mistakes it for a result.

**P2 — no constitutive arm passes [DISCRIMINATING; credence 95 %].**

- At ×1, ×0.1 and ×0.01 they fail C1 (P1).
- At ×0.001 synthesis is 0.0007 receptors/min, so the block barely moves a trained cell. Predicted:
  - C2 mean difference ≈ 0 (|Δ| < 0.01) → **fail**;
  - C4 → **fail**.
- **Counts against:** constitutive ×0.001 showing C2 Δ ≤ −0.05.

**P3 — labile × internalisation fails at every turnover [DISCRIMINATING; credence 85 %].**

- At ×1 to ×0.01 it fails C1 (P1).
- At ×0.001 it fails **C5**. During 12 h of level-4 training, internalised receptors are destroyed at k_des = 0.005/min
  (≈ 0.0025·S per minute at the I ≈ 0.5 S balance), and synthesis at 0.0007/min cannot replace them.
  - Total receptors fall from 35 to ~10 by the end of training.
  - The **control** cell's p at 90 min is then predicted ≈ 0.00–0.05, against ≥ 0.44 required.
- **Counts against:** control p at 90 min ≥ 0.44 in lab-int-kd0.001.
- The same applies to con-int-kd0.001, which already fails at P2.

**P4 — labile × gating × ×0.001 is the only arm that passes C1, C2, C4 and C5 [DISCRIMINATING; credence 60 %].**

- With gating nothing is destroyed, so the control recovers (C5 predicted p90 ≈ 0.85).
- Under the block X falls to 0.135 by the start of the short protocols, so reversion slows and habituation is faster:
  - C2 Δ predicted ≈ −0.2 to −0.4 in puro_short and chx_short;
  - C2 Δ predicted ≈ −0.05 to −0.15 in puro_short_15, where X is still 0.78 at the first tap. **This is the weakest
    link.**
- After 12 h, X ≈ e^(−12), so there is no recovery under the block: C4 Δ ≈ −0.8 at every delay.
- **Counts against:** any of those four failing in this arm.
- **Risk:** the published gate (C0). R6 (subliminal accumulation slows recovery) comes from destruction in the published
  model. With gating, total receptors are conserved, so R6's strict inequality may not hold. Credence that C0 passes
  in this arm: ~50 %.

**P5 — no arm passes both C2 and C3: "faster to the same floor" is out of reach [DISCRIMINATING; credence 85 %; the
main prediction].**

- Where the block accelerates habituation, it does so by removing recycling or reversion. That removes the floor, and
  the cell drains towards zero.
- At the end of 12 h, gating control sits at p ≈ 0.4. That is the balance I ≈ 0.5 S, S ≈ 23, λ ≈ 11.7.
- The blocked cell sits at p ≈ 0.
- So C3 |Δ| ≈ 0.4, against a tolerance of 0.10.
- Where the block leaves the floor alone (constitutive ×0.001), it also fails to accelerate.
- **Counts against:** any arm with C2 pass and C3 pass together.

**P6 — overall verdict [DISCRIMINATING].** **FAIL: no arm passes C0–C5.** Credence ~90 %.

- The predicted pattern is that labile-gating-×0.001 fails C3 alone (or C3 plus C0), and every other arm fails C1, C2
  or C5.
- If that holds, the minimal change the data call for is **not** in the receptor pools. The floor has to be set by
  something the block does not touch. An example is the two-state switch of Rajan et al. 2022. Testing that would be a
  new EID.

**Content (descriptive; reported, never counted). These describe what the model's cell keeps, answering the
operator's questions.**

- **D1 modality [POSITIVE CONTROL].** With two channels, training channel A leaves channel B's response exactly naive.
  This holds by construction, for independent pools.
- **D2 intensity.** R4, the hidden variable: habituation to a strong stimulus lowers the weak response, with no visible
  decrement in the strong one. Carried by S.
- **D3 history metamers [POSITIVE CONTROL].** Two different histories are reported with the distance between their
  (S, I) states:
  - 30 taps at 1/min then 10 min rest;
  - 60 taps at 4/min, then the rest time that brings it closest.
  
  The model's memory is at most **2 numbers per channel** (3 with the labile factor). Any history is summarised by
  those.
- **D4 polarisation.** The receptor potential at a tap falls with habituation while V_th stays fixed. This is
  consistent with Wood, as cited by Rajan 2022, who found the receptor potential falling and the action potential
  unchanged.
- **D5 longest memory.** Minutes after the 12 h control training until p is within 0.05 of naive.
  - Prediction: published model **30–90 min**, shorter than the 2–6 h forgetting Rajan 2022 report.
  - ×0.001 internalisation arms never return (P3).
- **Not representable, so not tested:**
  - position on the cell (one pool per channel; Stentor habituates globally, per Rajan 2022);
  - meaning or salience (the model has no evaluation stage; the literature shows none for single cells);
  - receptor type beyond the channel index.

## 3. Estimands and pass / fail criteria

The model is a deterministic ODE with deterministic jumps. The estimand is the contraction **probability** at each
tap (the authors' readout: P(open channels > n_min = 12), with n ~ Poisson(P_act·S)). There is no sampling, so the
**MCSE is 0**. The uncertainty is the integrator's: relative tolerance 1e-4, measured as model-v0.4.0's labile vs
constitutive agreement of ~1e-5. A criterion value within **1e-3** of its threshold is flagged *at threshold*. If a
passing arm is flagged, the verdict is UNINTERPRETABLE for that arm.

| Criterion | Estimand | Pass | Fail | Source of the target |
|---|---|---|---|---|
| C0 gate | R1–R8 (`neurotape.singlecell.gate`), block off | all eight | any | Rajan & Marshall 2025, Figs 2–7 |
| C1 baseline | untrained p_block − p_ctrl: one tap at 180 min (level 3 and 4), at 720 and 810 min (level 4) | every \|Δ\| ≤ 0.10 | any \|Δ\| > 0.10 | Rajan 2026, Fig 1C–F: untrained drug-treated cells contract like untreated |
| C2 acceleration | mean p over the training taps, block − control, in puro_short, chx_short and puro_short_15 | Δ ≤ −0.05 in all three | any Δ > −0.05 | Fig 1C, 1E, S1A: faster decay and lower habituated fraction |
| C3 same floor | long protocol, first test tap (2 min after training), block − control | \|Δ\| ≤ 0.10 | \|Δ\| > 0.10 | "similar contraction fractions at time 0 in Figures 1D and 1F" |
| C4 retention | long protocol, block − control at 20, 30, 60 and 90 min | Δ ≤ −0.05 at ≥ 2 of 4 | fewer than 2 | Fig 1D (20, 30, 90 min), 1F (30, 60, 90 min) |
| C5 control recovers | long protocol, control p at 90 min | ≥ 0.5 × untrained control at 810 min | below | 90 min restores "a sizeable fraction" of the response |

**Arm verdict.** An arm passes if C0–C5 all pass.

**Experiment verdict.**
- **PASS** if at least one arm passes and it still passes (C1–C5, with its C0) at every sensitivity setting (§6).
- **PASS (not robust)** if an arm passes at the main setting but fails at any sensitivity setting.
- **FAIL** if no arm passes.
- **UNINTERPRETABLE** if any run fails (a crash), or if a passing arm is flagged *at threshold*.

**Why these tolerances.** The paper reports "similar" and "improved" without effect sizes in its text. Its figures
are not machine-readable here. 0.10 for "similar" and 0.05 for "improved" are **[ARBITRARY]**: roughly the resolution
of a contraction fraction over ~30–60 cells. They were fixed before any protocol was run.

## 4. Falsifiers

- **Of the author's hypothesis** (no arm passes; P5): any arm passing C2 and C3 together. If an arm passes everything,
  the receptor structure with a labile recycling factor is sufficient. Then the case for a separate floor mechanism
  (the two-state switch) is weakened, and E04 would not be needed.
- **Of the labile-factor idea specifically:** if lab-gate-kd0.001 fails C2 or C4, a synthesis-dependent recycling
  factor does not even produce the direction of the drug effect in this structure.
- **What would close this line:** a FAIL with P5's pattern. That closes minimal edits to the receptor pools as an
  account of Rajan 2026, and moves the question to the floor mechanism.

## 5. Model specification

Rajan & Marshall 2025 receptor inactivation, time in **minutes**. Per channel c:

```
dS/dt = k_syn·syn·s − k_deg·s·S + k_rec·X·I
dI/dt = −k_rec·X·I − (k_deg·s + k_des)·I          (internalisation)
dI/dt = −k_rec·X·I − k_deg·s·I                    (gating: modified in place, never destroyed)
dX/dt = k_x·(syn − X)   with X ≡ 1 when recycling is constitutive
at a tap of force F:  P_act = 1/(1 + e^(−0.6(F − 1.5)));  λ = P_act·S;  p = 1 − PoissonCDF(12; λ);  S −= 0.1·P_act·S, I += same
```

- `syn` = 1, or 0 under the block, from t = 0.
- `s` = k_deg_scale.

| Parameter | Value | Tag |
|---|---|---|
| k_int, k_rec, k_syn, k_deg, k_des | 0.1, 0.1 /min, 0.7 /min, 0.02 /min, 0.005 /min | [LIT: 10.1016/j.cub.2025.05.071] |
| F_mid, scale, S_a, S_b, V_th | 1.5, 0.6, 1000, 0.00025, 0.012 | [LIT: same] |
| V_i, io_max | 1, 1 | [LIT: the authors' code convention] |
| n_min | 12.0 | [DERIVED: (V_th/V_i)·S_a / (1 − (V_th/V_i)·S_b)] |
| S* | 35 | [DERIVED: k_syn/k_deg; unchanged by s] |
| k_deg_scale s | 1, 0.1, 0.01, 0.001 | [ARBITRARY: decade grid; the lowest is the value P1's closed form needs for C1] |
| k_x | 1/60 /min (τ = 1 h) | [ARBITRARY: a short-lived protein; sensitivity 1/20, 1/180] |
| synthesis block | syn = 0 (complete) from t = 0 | [ARBITRARY: the doses "significantly impair" synthesis; a partial block is not modelled] |
| level 3 → F, level 4 → F | 1.0, 1.5 | [ARBITRARY: the tapper levels are not in R&M's force units; chosen so level 4 habituates at 1/min (Rajan 2022) and level 3 more; sensitivity ±0.5] |
| gate forces (low, high) | 1.0, 4.0 | [ARBITRARY: as in model-v0.3.0's gate] |

## 6. Design

**Arms.**

- The 2 × 2 × 4 factorial in §1 gives **16 arms**.
- Every arm runs every protocol twice, as **control** (syn = 1) and **block** (syn = 0 from t = 0).
- The arm con-int-kd1 is the published model.

**Protocols** (Rajan et al. 2026, Methods):

| Protocol | Pre-treatment | Force | Rate | Training | Test taps |
|---|---|---|---|---|---|
| puro_short (Fig 1C) | 120 min in drug | level 3 | 1 tap/min | 60 taps | — |
| chx_short (Fig 1E) | 120 min | level 4 | 1 tap / 2 min | 30 taps | — |
| puro_short_15 (Fig S1A) | 15 min | level 3 | 1 tap/min | 60 taps | — |
| long (Fig 1D/F) | none | level 4 | 1 tap/min | 720 taps (12 h) | real level-4 taps at 2, 5, 10, 20, 30, 60, 90 min after the last training tap |
| untrained_short | — | level 3; level 4 | — | — | one tap at 180 min (a naive cell per tap) |
| untrained_long | — | level 4 | — | — | one tap at 720 min; at 810 min (a naive cell each) |

**Seeds.** None: the model is deterministic, and its readout is a probability. The viewer's sampled cell uses seed 0
(display only).

**Runs.** Main: 16 arms × 6 protocols × 2 = **192 runs**, plus R1–R8 per arm (16). The stopping rule is to run
everything once; there is nothing to stop early.

**Sensitivity.**

- One at a time, every arm, C1–C5 re-scored (C0 does not depend on these):
  - force_low: level 3/4 = 0.5/1.0;
  - force_high: level 3/4 = 1.5/2.0;
  - kx_fast: k_x = 1/20;
  - kx_slow: k_x = 1/180.
- That is **768 runs**.
- **Rule:** a main-setting pass that fails at any sensitivity setting is reported as **not robust**. A main-setting fail
  that passes somewhere is reported with the setting, and does not change the verdict.

**Content runs (D1–D5).** Per arm, block off. Descriptive.

**Exclusions.** None. A crashed run is kept in `runs.json` with its traceback and makes the verdict UNINTERPRETABLE.
It is never re-run silently; a re-run is a deviation.

**Order.** `main` → `sensitivity` → `content` → `export` → `analyse.py`.

## 7. Environment

| Item | Value |
|---|---|
| Language | CPython 3.11.16 (uv), macOS 26.5 arm64 |
| `ENV.lock` sha256 | `840360fb3f17819035904926c97a8f97c3a80cdbb93cbf8b337a1a5bf907eb18` |
| Simulator | libRoadRunner 2.10.0 (CVODE, default tolerances) via tellurium 2.2.13.1 — peer-reviewed (Somogyi et al. 2015; Welsh et al. 2023) |
| Known conflict | libroadrunner declares numpy ≥ 2.2; numpy is 1.26.4 for Brian2. The 17 singlecell tests pass on this pair. Recorded in ENV.lock |
| Code | `src/` must equal `model-v0.4.0` (`run.py` refuses otherwise) |
| Reproduction tolerance | `runs.json` byte-identical on re-run on this machine. Other platforms: agreement to 1e-4 relative, not bit-for-bit |

## 8. Prior knowledge and calibration

**Seen before this tag:**

- **Rajan et al. 2026 [FT].** The text, Methods and protocol descriptions were read in full through the research
  library, 2026-09-25. **Figure values were not read**: the figures are not in the text layer. The criteria use only
  the text's statements.
- Rajan & Marshall 2025 [FT] and their MATLAB.
- Rajan et al. 2022 [FT].
- E02's Arm R result: the untrained baseline drains under a block in a graded network.
- The model-v0.3.0 gate values:
  - force 1: 0.724 → 0.291 over 60 taps;
  - recovery half-time 7 min after 20 taps, 9 min after 200.

**Calibration.**

- Nothing in the model was fitted to Rajan 2026.
- The one choice informed by the target is the **k_deg_scale grid**. Its lowest value (×0.001) is the decade that
  P1's closed form shows C1 needs. C1 at ×0.001 is therefore a **positive control, not a prediction**. It is labelled
  so in P1.
- k_x = 1/60 was chosen as "a short-lived protein" before any protocol was simulated. It was not tuned.
- The force mapping was chosen before any protocol was simulated.

**Held out:** C2–C5 for every arm, and C0 for the gating and slow-turnover arms.

**Pilots** (`exploratory/pilot/`, never cited):

| # | Step | What was run | What was seen | What it set |
|---|---|---|---|---|
| U1 | Closed-form untrained S(t) and p under the block | arithmetic, no simulator protocol | P1's table | the k_deg grid's lowest decade |
| U2 | `smoke.py`: run.py and analyse.py end to end on a synthetic protocol set (forces 0.7/1.2, 5-tap and 60-tap training, 8 arms, 1 sensitivity setting) | 192 runs + 8 gate rows + 8 content rows | **ran/crashed only; no criterion value printed** | no change (nothing crashed) |
| U3 | `export` on a 5-tap synthetic protocol | 1 export | wrote a file | no change |
| U4 | model-v0.4.0 tests | 17 tests | labile vs constitutive differ by ~1e-5 without a block | the 1e-4 tolerance |

**Unregistered steps before the tag:** none.

## 9. Adaptive stages

- None planned.
- If P4's arm passes C0–C5 but is not robust, no new stage follows here. A follow-up is a new EID.

## 10. Open decisions (decided here, before any protocol run)

1. **Block onset** at t = 0 in every protocol, including the pre-treatment. Untrained cells are in drug for the whole
   interval.
2. **Test taps after training are real stimuli.** They internalise, as in the experiment, where every tap is a tap.
3. **Untrained cells get one tap each.** A naive cell per time point, matching the paper's single-tap design.
4. **Acceleration measure** = the mean p over all training taps. The paper's "faster decay and lower final fraction"
   together is closer to an area than to either alone. Final-tap values are reported beside it.
5. **Time 0** = the first test tap, 2 min after training. The paper's "0 minutes" is the end of training; the first
   tested point in Methods is 2 min.
6. **C5 reference** = untrained control at 810 min (13.5 h), the same drug-free time point as the 90-min test.
7. **One tap per minute** means taps at pre_min, pre_min + period, and so on. The first tap is at the end of
   pre-treatment.
8. **Gate R1–R8 is run with the block off.** The labile factor is inert there (X = 1), so the gate is run once per arm.
9. **Exports for the viewer:** con-int-kd1 (published) and lab-gate-kd0.001 (the P4 candidate), puro_short and long,
   control and block. These are chosen now, whatever the results.

## 11. Timestamp / archive

- The `E03-synthesis-block-prereg` tag is made with `.agents/tools/tag`. Its receipt is posted to the experiment PR
  (polarizetech/neural-memory#9), which carries GitHub's server timestamp.
- **No Zenodo, SWHID or RFC 3161 receipt.** Local git history plus the PR receipt are all there is.
