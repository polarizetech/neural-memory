# E03-synthesis-block — Results

Run tag: E03-synthesis-block-run   Model tag: model-v0.4.0
ENV.lock sha256: 840360fb3f17819035904926c97a8f97c3a80cdbb93cbf8b337a1a5bf907eb18
Runs: 192 main, 16 gate, 768 sensitivity, 16 content, 8 exports. **Failed: 0.**
Reproducibility: `main` re-run gave byte-identical `runs.json` and `gate.json`.
Attempt: 2 on this question. The earlier attempt was E02-local-negative-image, Arm R: FAIL, because the untrained
baseline drains in a graded network.

**These are statements about the models. They are not evidence about Stentor.**

## 1. Criteria table (main setting; thresholds verbatim from PREREG §3)

P = pass, F = fail.

| Arm | C0 gate | C1 baseline | C2 accel | C3 same floor | C4 retention | C5 recovery | Arm |
|---|---|---|---|---|---|---|---|
| con-inte-kd1 (published) | P | F (−0.89) | P | F (0.47 vs 0.00) | P | P | FAIL |
| con-inte-kd0.1 | F (R3) | F | P | P (0.04 vs 0.00) | P | F (0.33) | FAIL |
| con-inte-kd0.01 | F (R3, R6) | F (−0.17) | F | P (0.00 vs 0.00) | F | F (0.01) | FAIL |
| con-inte-kd0.001 | F (R3, R6) | P | F (−0.003) | P (0.00 vs 0.00) | F | F (0.003) | FAIL |
| con-gati-kd1 | F (R6) | F | P | F | P | P | FAIL |
| con-gati-kd0.1 | F (R6) | F | P | F | P | P | FAIL |
| con-gati-kd0.01 | F (R6) | F | F (−0.035) | F (0.47 vs 0.28) | P | P | FAIL |
| con-gati-kd0.001 | F (R6) | P | F (−0.004) | P (0.47 vs 0.45) | F | P | FAIL |
| lab-inte-kd1 | P | F | P | F (0.47 vs 0.00) | P | P | FAIL |
| lab-inte-kd0.1 | F (R3) | F | P | P (0.04 vs 0.00) | P | F (0.33) | FAIL |
| lab-inte-kd0.01 | F (R3, R6) | F | P | P (0.00 vs 0.00) | F | F (0.01) | FAIL |
| lab-inte-kd0.001 | F (R3, R6) | P | P | P (0.00 vs 0.00) | F | F (0.003) | FAIL |
| lab-gati-kd1 | F (R6) | F | P | F | P | P | FAIL |
| lab-gati-kd0.1 | F (R6) | F | P | F | P | P | FAIL |
| lab-gati-kd0.01 | F (R6) | F | P | F | P | P | FAIL |
| **lab-gati-kd0.001** | **F (R6)** | P (−0.013) | P (−0.23 / −0.43 / −0.15) | **F (0.47 vs 0.00)** | P (−0.82 … −0.89) | P (0.886 / 0.888) | FAIL |

- No value is flagged *at threshold*.
- Sensitivity (force ±0.5, k_x = 1/20 and 1/180): **no arm passes C1–C5 at any setting.**

## 2. Verdict

**FAIL.** No arm passes C0–C5, at the main setting or at any sensitivity setting.

## 3. Predictions against outcome

| Prediction | Outcome |
|---|---|
| P1 (closed form, positive control): C1 passes only at ×0.001 | As computed. The published model's untrained cell goes from 0.72–0.89 to 0.000 after 3 h of block, with its own hard threshold |
| P2: no constitutive arm passes; at ×0.001, C2 \|Δ\| < 0.01 | **Held.** C2 Δ = −0.001 to −0.004 |
| P3: labile × internalisation fails at every turnover; at ×0.001, control p at 90 min ≈ 0–0.05 | **Held.** 0.003 |
| P4: lab-gati-kd0.001 passes C1, C2, C4 and C5; C0 at ~50 % | **Held on C1, C2, C4 and C5.** puro_short_15 gave −0.15, inside the predicted −0.05 to −0.15. **C0 failed on R6**, the named risk |
| P5: no arm passes both C2 and C3 | **Falsified as written, in four arms**: con-inte-kd0.1, lab-inte-kd0.1, lab-inte-kd0.01 and lab-inte-kd0.001. See below |
| P6: FAIL, with lab-gati-kd0.001 failing C3 (and C0) | **Held.** Pattern as predicted |

**P5 is falsified, but only degenerately.**

- Each of those four arms passes C3 because the **control** cell is also at or near zero after 12 h (0.000–0.040).
  With receptors being destroyed and slowly resynthesised, 12 h of training kills the control's response too.
- The same arms fail C5 (0.003–0.33 against 0.44). So they satisfy C3 in a way the paper's cells, which do recover,
  do not.
- C3 as preregistered did not guard against a shared floor at zero. **That is a gap in the criterion, recorded here
  rather than patched.**
- The substantive claim behind P5 survives: every arm that reaches the **same, non-zero** floor fails C2 or C4. But
  that claim is post hoc, and it is labelled so.

## 4. Patterns the model FAILED to reproduce

- **The same habituated level with and without the block (Rajan 2026, Fig 1D/F).**
  - In every arm where the control keeps a non-zero floor (0.47–0.55), the blocked cell drains to 0.000.
  - The block removes recycling, or the synthesis that feeds it. In this structure that is what sets the floor.
- **Untrained cells unaffected by the block**, at the published turnover. This is E02's result, now with the paper's
  own hard threshold.
- **R6, subliminal accumulation (Rajan & Marshall 2025).**
  - It fails in **every gating arm**: recovery half-time is 7 min after 20 taps and after 200.
  - With nothing destroyed, recovery depends only on the (S, I) state, not on how long training went on beyond
    saturation.
  - In the published model R6 comes from destruction of internalised receptors.
- **R3, force dependence**, fails in **every internalisation arm with slowed turnover** (×0.1 and below).
  - The high-force response falls to 0.68–0.70 of naive after 60 taps, against the gate's > 0.8.
  - Destroyed receptors are replaced too slowly.
- **Recovery after long training** fails in internalisation arms at ×0.1 and below (C5).
- Across the whole factorial, the published model's own behaviours (R3, R6) and Rajan 2026's baseline (C1) pull
  turnover in opposite directions:
  - R3 and R6 need destruction plus fast replacement;
  - C1 needs slow replacement.

## 5. Sensitivity

- force_low, force_high, kx_fast, kx_slow: **0 of 16 arms** pass C1–C5 at any setting.
- The verdict does not depend on the force mapping or on the labile factor's lifetime.

## 6. Content (descriptive; not counted)

| | Published (con-inte-kd1) | lab-gati-kd0.001 | lab-inte-kd0.001 |
|---|---|---|---|
| D1 modality: channel B after 60 taps on A | 0.724 = naive 0.724 (A: 0.29) | 0.724 = naive (A: 0.27) | 0.724 = naive (A: 0.20) |
| D3 history metamer: (S, I) distance between 30 taps at 1/min + rest and 60 taps at 4/min + rest | 0.27 receptors, at 31.8 min | **0.002**, at 32.0 min | 0.42 |
| D4 receptor potential, first → 60th weak tap (V_th = 0.012) | 0.0149 → 0.0108 | 0.0149 → 0.0106 | 0.0149 → 0.0099 |
| D5 minutes after 12 h training until p is within 0.05 of naive | 30 | 20 | never (in 24 h) |

- Across all 16 arms D5 is 15, 20, 30 or 1010 min, or never.
- The published model forgets in **30 min**. That is at the low end of the predicted 30–90 min, and shorter than the
  2–6 h Rajan 2022 report.
- **D1:** modality is kept perfectly, by construction.
- **D3:** in the gating arm two different histories reach the same state to 0.002 receptors. After that, the cell
  cannot tell them apart.
- **D4:** habituation appears as a smaller receptor potential dropping below threshold, not as a changed threshold.

## 7. Deviations and unregistered steps

- None. `DEVIATIONS.md` is empty.
- The C3 degeneracy (§3) is reported as a property of the criterion. It was not fixed.

## 8. What this means for the next question (not a result)

- The receptor-pool edits tested here cannot give "faster to the same floor". Any edit that makes the block speed
  habituation also removes the floor.
- The two constraints that break the pools come from opposite directions:
  - Rajan & Marshall's own R3 and R6 need fast turnover;
  - Rajan 2026's baseline needs slow turnover.
- The floor, and possibly the retention, would have to come from a state the block does not touch. The candidate
  named in the preregistration is Rajan et al. 2022's two-state switch. That would be a new EID, with C3 tightened to
  require a non-zero control floor.
