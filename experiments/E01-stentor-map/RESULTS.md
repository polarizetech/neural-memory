# E01-stentor-map — Results
Run tag: E01-stentor-map-run   Model tag: model-v0.1.0   ENV.lock sha256: d3f81994cb32cedb5d54675935c6f98f94f6f4eec2748deb8c9fde5bffe57e20   Runs: 90, failed: 0

- Ran 2026-09-24, 13:04–13:09 −07:00: `run.py all --workers 8`, gates passed (prereg tag → ead2b99).
- Every number below is from `outputs/summary.json`, written by the frozen `analyse.py`, except where marked
  **[MDE rule]** (DEVIATIONS #1 and #4) or **[EXPLORATORY]**.
- Predicted values are the analytic model's, from PREREG §2. They are **efficacy**; observed values are **spikes**.
- Read depth: the Stentor sources are [USER] — supplied, not read here. So every "Stentor predicts" below is the
  operator's summary of them, not a quotation.

## 1. Criteria table

| Criterion | Pre-registered threshold | Pre-registered value (efficacy) | Observed (spikes, 10 seeds) | Pass/Fail |
|---|---|---|---|---|
| SR1-std (a) | seed-mean D16 strictly increasing over ×1, ×0.25, ×0.1, frozen | 0.126 → 0.494 → 0.624 → 0.728 | **0.057 → 0.418 → 0.597 → 0.765** | PASS |
| SR1-std (b) | seed-median half-decrement point non-decreasing, frozen > ×1 | 4 → 6 → 6 → 7 | **4 → 5.5 → 8 → 8** | PASS |
| **SR1-std** | (a) and (b) | — | — | **PASS** |
| SR1-hebb_only (null) — D16 | every per-seed ΔD16 vs ×1: 95 % CI contains 0 and \|mean\| < 0.05 | no change (recovery over 48 s < 1.3 %) | ×0.25 −0.001 [−0.017, +0.015]; ×0.1 +0.000 [−0.010, +0.010]; frozen +0.007 [−0.010, +0.023] | holds |
| SR1-hebb_only (null) — half point | seed-median half point identical across all four | unchanged | **4 → 4 → 4.5 → 4.5** | broken |
| **SR1-hebb_only** | both | — | — | **FAIL** |
| SR3-std | 95 % CI upper < 0 for both inserts | −0.21 % (+10 dB), −0.33 % (+20 dB) | +10: **−0.69 % [−2.27, +0.89]**; +20: **−0.93 % [−3.65, +1.79]** | analyse.py: FAIL → **[MDE rule] UNINTERPRETABLE** (both \|effect\| < MDE 3.50 %) |
| SR3-hebb_only | same | deepening, size not derived | +10: **−0.74 % [−2.71, +1.24]**; +20: **−3.46 % [−5.92, −1.00]** | analyse.py: FAIL → **[MDE rule] UNINTERPRETABLE** (+10 under MDE 1.25 %; +20 beyond it and deepening) |
| SR2 | none — measurement only | slope +28.7 (0.03–0.3 Hz), +19.8 (0.1–1 Hz) for `std` | `std` periodic: **not computable** in either window (a mean D ≤ 0 in the window); see §3 and §5 | — |

**Under the stricter reading of DEVIATIONS #4 (analyse.py's own verdict), both SR3 arms are FAIL.** Under the MDE
rule, applied per insert, both are UNINTERPRETABLE. Neither reading gives a PASS.

## 2. Verdict

- **SR1-std: PASS.** Slowing the slow pool's recovery deepened the decrement at every step, and moved the
  half-decrement point later, as the analytic cascade predicted.
  - The spike decrement at the normal recovery (0.057) is half the predicted efficacy decrement (0.126). By
    frozen it exceeds it (0.765 vs 0.728): the cells' threshold compresses small efficacy changes and expands
    large ones.
- **SR1-hebb_only: FAIL**, on the half-point clause only.
  - The substantive null holds: no D16 change beyond ±0.023 at any recovery scale.
  - But the seed-median half point moved 4 → 4.5, because a threshold crossing on a noisy 16-point curve jitters
    between neighbouring presentations when the spike trains diverge.
  - "Identical medians" was too brittle a test for a quantity with this much noise. That is a fault in my
    criterion, and it stays a FAIL.
- **SR3-std: UNINTERPRETABLE.** Both effects are about ¼ of the minimum detectable effect, as DEVIATIONS #1
  predicted before the run.
- **SR3-hebb_only: UNINTERPRETABLE** under the MDE rule; FAIL under analyse.py's frozen rule. A strong
  (+20 dB) insert **deepened** the next response by 3.5 %, beyond the MDE and with the CI below zero. The +10 dB
  effect was too small to call.
- **Across both arms, no insert produced dishabituation:** no CI lies above zero, so the PREREG §4 falsifier did
  not fire.
- **SR2: measurement, unresolved in the preregistered windows.**
  - `std`'s decrement is at or below the measurement floor for 0.01–0.1 Hz, so 20·log₁₀D is undefined there.
  - `hebb_only`: −1.26 dB/decade [−1.42, −1.10] (0.03–0.3 Hz), i.e. flat to slightly *more* decrement at low
    rates, as predicted.
- **Overall: FAIL** (PREREG_PROTOCOL rule 3: a failed pre-registered criterion closes the version). One criterion
  passed, one failed, two are uninterpretable, and SR2 was not resolved.

## 3. Patterns the model FAILED to reproduce

1. **Stentor's longer retention after a resynthesis block: not reproduced by the depression cascade.**
   - `std` retention at 30 min was **0.000 at ×1 and ×0.25**, as predicted (both recover to the same steady state).
   - At ×0.1 and frozen the treatment-matched control fell to the floor (9/10 and 10/10 seeds), so retention there
     is **unmeasurable**. At ×0.1 that was *not* predicted; the prediction was a measurable 0.000.
   - In `hebb_only`, retention did rise with slower recovery: **0.146 → 0.282 → 0.324 → 0.358**, with recognition
     0.040 → 0.134. **But the floor rule excluded 0, 2, 3 and 4 seeds respectively**, so the later means come from
     the seeds whose controls did not drain. That selection can bias upward.
   - This is the one place the Stentor retention pattern appears, and it is the non-primary arm, on shrinking n.
2. **Stentor's "faster decrement" after a block: the opposite in `std`.** The half-decrement point moved *later*
   (4 → 8) while the final decrement deepened. It was predicted that way before the run, and it is still a mismatch
   with the organism.
3. **SR2: no decrement–rate slope could be measured where it was preregistered.**
   - `std` periodic D at 0.01 / 0.03 / 0.1 Hz: −0.030 / −0.022 / −0.008, every CI containing 0.
   - The plasticity-off arm (`none`) is ±0.03 at every rate, which sets the floor. The predicted efficacy D there
     (4 × 10⁻⁵, 0.004, 0.036) is below it.
   - The analytic +28.7 and +19.8 dB/decade therefore went **untested**, and no comparison with Stentor's
     −30 dB/decade is possible. **The sign-convention open item (PREREG §9, item 7) stays open**; it still needs the
     Escobedo et al. 2026 full text.
4. **The SR3 silent-gap control did not show the predicted recovery in `std`:** predicted +3.3 % (efficacy),
   observed +0.1 % [−2.1, +2.3]. In `hebb_only` it was +3.1 % [−0.1, +6.4].
5. **The magnitude of every `std` effect was smaller in spikes than in the analytic efficacy** at small effects:
   D16 at ×1 was 0.057 against 0.126, and SR2 at 0.3 Hz was 0.050 against 0.114. The analytic model sets direction,
   not size, through a threshold nonlinearity.

## 4. Sensitivity

The [ARBITRARY] parameters (PREREG §5) were **not swept**: U = 0.5, a_slow = 0.05, the relay mapping, τ_L = 1 h,
the post-trace τ, and the E/I weights.

- **SR1-std's direction** follows from the cascade's structure: any a_slow > 0 with a finite recovery deepens
  with slower recovery, per the analytic model. Its **magnitude** would move with a_slow and U. So the PASS is not
  a property of the chosen a_slow, but the numbers are.
- **SR3 and SR2 were decided by noise, not by a parameter.** Both verdicts hinge on the measurement floor (the
  MDE; the `none`-arm ±0.03), which depends on spontaneous rate, cell count and seeds more than on any
  plasticity value.
- The floor rule's factor (2× spontaneous) decides how many SR1 seeds drop out at ×0.1 and frozen. It was
  preregistered and not varied.

## 5. Controls

- **`none` (plasticity off):**
  - SR1: D16 −0.001 [−0.024, +0.022], retention and recognition exactly 0.
  - SR2: D within ±0.03 at every rate (this is the measurement floor used above).
  - SR3: every effect exactly 0.000, because the series are paired with identical draws and nothing plastic
    differs. This confirms the SR3 pairing.
- **SR2 shuffled onsets vs periodic.**
  - `std` shuffled is resolvable one step lower (0.1 Hz: +0.025, 0.3 Hz: +0.125 vs periodic +0.050). Only the
    secondary window is computable: **+22.5 dB/decade [+12.7, +40.4]** against the analytic periodic +19.8.
    Shuffled is a control, not the preregistered periodic measurement.
  - `hebb_only` shuffled ≈ periodic (−1.22 vs −1.26 dB/decade).
- **SR3 silent gap:** see §3 item 4. It raised `hebb_only` by +3.1 % and moved `std` by nothing.
- **Time- and treatment-matched SR1 control:** this is what makes the frozen and ×0.1 retentions unmeasurable.
  It is the correct control; its floor is a result.

## 6. Exploratory (clearly labelled)

**[EXPLORATORY] Is SR2's negative slow-rate decrement a fast-forward artefact?** No.

- Source: `exploratory/ff_vs_direct.py` and `.json`. Same arm (`std`), stimulus and seeds, 0.1 Hz periodic, with
  gaps fast-forwarded as in `run.py` vs simulated directly: D −0.0078 (identical to SR2) vs **−0.0040**, per-seed SD
  0.068 and 0.063.
- Both are zero within a standard error of ~0.02, so the negative values are noise on a decrement too small to
  resolve, not facilitation.
- 0.03 Hz: see the addendum at the end of this section.
- Also exploratory, computed from the preregistered outputs but over windows that were NOT preregistered: `std`
  periodic from its resolvable points gives +25.4 dB/decade over 0.3–1 Hz and +15.8 over 1–3 Hz. The analytic
  equivalents are +18.8 and +13.6. Not evidence for anything preregistered.

## 7. What only worked because it was tuned

- **`hebb_only`'s rate (η ×¼) was chosen after step 2's results,** as the best of three declared rates. The arm
  was carried into E01 *because* it recognised. Any `hebb_only` result here is conditioned on that selection.
- **The network operating point** (I0 = 80 pA, w_in = 8 nS) was tuned, against firing-rate criteria only, never
  against any E01 quantity.
- **The SR3 MDE rule was adopted before the run** (DEVIATIONS #1, outcome not known), after the analytic prediction
  showed SR3-std was undetectable. It changed the SR3-std call from FAIL to UNINTERPRETABLE. It is not a tuning of
  the model, but it is a rule chosen knowing which way it would cut.
- **SR1-std's PASS: nothing tuned.** The direction was predicted from structure, and no parameter was moved for
  or after it.

## 8. Next EID

This experiment is closed with verdict **FAIL** (SR1-hebb_only). E02 would change the following:

- **The null half-point test:** equivalence on the *mean* half point with a stated tolerance (e.g. ±1
  presentation), not identical medians.
- **SR2's resolution:** average several first responses (or a steady-state reference) instead of the single R1;
  add seeds so the `none` floor is well under the predicted D at 0.03–0.1 Hz; and keep 0.01 Hz reported only.
- **SR1 retention:** a design whose control does not drain. For example, block recovery without spontaneous
  release during the delay, or probe earlier than the floor at ×0.1. Either way, "longer retention" becomes
  measurable in the primary arm.
- **SR3:** an MDE computed for the paired design itself (from the `none` arm's exact-zero pairing, the paired
  variance is far smaller than the proxy used here), or more seeds, so that a −1 % effect is callable.

---

### Addendum to §6 (exploratory, 0.03 Hz)
At 0.03 Hz, fast-forwarded gaps give D −0.0220 (identical to SR2), and directly simulated gaps give **−0.0155**.
Per-seed SD is 0.065 and 0.069. Both are zero within noise, and fast-forward vs direct differ by 0.007, well
inside it. The fast-forward is **not** the cause of SR2's unresolved slow-rate decrement: the decrement there is
below the floor of a single-first-response measurement at 10 seeds.

## Post-close review — 2026-09-25

A review of the analysis (docs/REVIEW.md) found two things. Nothing above is edited.

1. **The "MDE" in DEVIATIONS #1 has no power term.** t(0.975, 9)·SD/√10 is the 95 % CI half-width, i.e. the
   effect detectable with about 50 % power. With 80 % power the values rise about 1.39×, to 4.9 % (`std`) and
   1.7 % (`hebb_only`). No verdict changes: SR3-`std` stays UNINTERPRETABLE and SR3-`hebb_only`'s +20 dB effect
   (−3.46 %) still exceeds it.
2. **The SR2 bootstrap intervals are conditional.** Resamples whose mean decrement is ≤ 0 are dropped before
   taking percentiles (for `std|shuffled`, 1624 of 2000 survive), so those intervals are conditioned on a
   positive decrement and biased upward. They were reported as controls, not verdicts.
3. **SR2 `hebb_only` has no time-matched control.** The Hebbian factor erodes in silence (docs/REVIEW.md, R1):
   at 0.03 Hz the 500 s train alone costs about 25 % efficacy. The "slightly more decrement at low rates"
   (−1.26 dB/decade) is therefore plausibly an erosion artefact, not a rate effect. SR1 is time-matched and is not
   affected.
