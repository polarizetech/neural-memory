# E01-stentor-map — Do the synaptic-depression substrate's habituation dynamics reproduce three single-cell (Stentor) constraints?
Preregistered: 2026-09-24   Model tag: model-v0.1.0   Author: LLM session (Claude Opus 5.5) + Joshua Anderton

Read depth: [USER] supplied by the operator, not read here · [AB] abstract · [FT] full text or the quoted passage
· [BG] background knowledge. Stentor sources: Rajan et al. 2026 (doi 10.1016/j.cub.2026.03.080) [USER];
Escobedo et al. 2026 (doi 10.64898/2026.06.06.730631) [USER]; Ramdas et al. 2026 (doi 10.64898/2026.06.09.731162)
[USER]; Rajan & Marshall 2024 (doi 10.1101/2024.11.05.622147) [USER]. Model sources: Tsodyks & Markram 1997
(doi 10.1073/pnas.94.2.719) [FT, the model passage]; Ulanovsky et al. 2004 (doi 10.1523/JNEUROSCI.1905-04.2004) [AB].

## 1. Question
Does the two-pool synaptic-depression cascade of `neurotape.habituation`, and separately its recognising
anti-Hebbian arm, show three signatures reported for habituation in the single-celled *Stentor*? The signatures are:

- **SR1:** blocking resynthesis gives faster decrement and longer retention.
- **SR2:** a decrement magnitude that rolls off with presentation rate at a measurable slope.
- **SR3:** a strong stimulus deepens rather than dishabituates.

**Limit (stated up front).** With `std` as the primary arm, SR1–SR3 test the *depression cascade*, not the
recognising arm. In steps 1–2, `std` habituated non-specifically and never recognised the stored sound. `hebb_only`
is run beside it, as the secondary arm for SR1 and a full arm for SR2 and SR3. A pass here says the cascade's
*dynamics* resemble Stentor's; it says nothing about memory specificity.

The results do not transfer to the 1.5 s stimuli of steps 1–2: every SR run uses a 0.2 s stimulus.

## 2. Prediction(s) — risky, numeric, directional
All predictions come from `neurotape.habituation.analytic` (the two pools as deterministic ODEs, driven by the real
Zilany-AN relay rates of each seed's 0.2 s stored sound, no network), averaged over the 10 seeds. They predict
**efficacy**, not spikes. Scored quantities are spikes, so these give direction and order of magnitude.

- **P1 (SR1, `std`).** Slowing the slow-pool recovery (×1 → ×0.25 → ×0.1 → frozen) deepens the decrement and
  moves the half-decrement point later.
  - Efficacy decrement at presentation 16: **0.126 → 0.494 → 0.624 → 0.728**.
  - Half-decrement presentation: **4 → 6 → 6 → 7** (identical in all 10 seeds).
  - *Counts against it:* the decrement does not deepen monotonically, or the half point moves earlier.
  - Note: Stentor's "faster decrement" is **not** what this model predicts. The half-point, measured against its
    own final level, moves *later*, because the final level deepens more than the early fall steepens.
- **P2 (SR1, `std`, retention at 30 min).** Retention (suppression of the stored sound against a time-matched,
  treatment-matched control) is **0.000 at ×1, ×0.25 and ×0.1**: with τ_slow ≤ 200 s, both recover to the same
  steady state within 1800 s.
  - When frozen, spontaneous release drains trained *and* control to ~0. The efficacy ratio predicts 0.41, but both
    spike responses are expected at the floor. **Predicted: uninterpretable (floor).**
  - So Stentor's "longer retention" is predicted *not* to appear.
  - *Counts against this prediction:* retention > 0 at ×0.25 or ×0.1.
- **P3 (SR1, `hebb_only`, predicted null).** Scaling the 1 h long-term recovery by ×0.25, ×0.1 or frozen leaves the
  16-presentation decrement unchanged. Recovery over the 48 s series is < 1.3 % at ×1.
  - *Counts against it:* a decrement change beyond the §3 equivalence margin.
  - Retention at 30 min is predicted to *increase* with slower recovery (direction only; not a criterion).
- **P4 (SR2, measurement).** Decrement magnitude D (efficacy, `std`, periodic, 16 presentations, mean of the last 4):

  | rate (Hz) | 0.01 | 0.03 | 0.1 | 0.3 | 1 | 3 |
  |---|---|---|---|---|---|---|
  | D (efficacy) | 4.1e-5 | 0.0042 | 0.0360 | 0.1138 | 0.3531 | 0.7440 |

  - Slope over **0.03–0.3 Hz: +28.7 dB/decade**. Over **0.1–1 Hz: +19.8 dB/decade**.
  - *Sign convention:* 20·log10 D per decade of *increasing* rate (D is an amplitude-like magnitude, so 20 log10).
  - A single first-order stage gives +20 dB/decade only where the onset period is much shorter than its recovery
    time. Below that the decrement falls off exponentially, so the local slope steepens without limit and does not
    count stages.
  - `hebb_only`: predicted ≈ 0 dB/decade or negative. Its only slow variable recovers with τ = 1 h, much longer
    than every period. Spontaneous erosion over the longer low-rate sessions (1600 s at 0.01 Hz) can only *raise*
    the low-rate decrement.
- **P5 (SR3).** For `std`, inserting a louder presentation at 8 deepens the response to presentation 9 by only
  **−0.21 % (70 dB) and −0.33 % (80 dB)** in efficacy. Release saturates, so a louder sound depletes the pools little
  more.
  - The silent-gap control *raises* it by **+3.3 %**.
  - `hebb_only`: deepening predicted (anti-Hebbian depression scales with the larger postsynaptic response). The
    magnitude is not derived.
  - *Counts against it:* the response at 9 is higher after a loud insert than in the unperturbed series
    (dishabituation).

## 3. Pass / fail criteria (numbers written before any output is seen)
Computed by `analyse.py` (frozen with this file) from `outputs/*/runs.json`.

- **Responses:** R_n = E spikes during presentation n's 0.2 s, minus the expected spontaneous count (the run's
  measured spontaneous rate × 200 cells × 0.2 s).
- **Decrement at 16:** D16 = 1 − R16/R1.
- **Half-decrement:** first n with R_n ≤ R1 − ½(R1 − R16); the absolute version R_n ≤ ½R1 is reported beside it.

| Criterion | Metric | Pass threshold | Fail threshold | Pre-registered value/derivation |
|---|---|---|---|---|
| SR1-std (a) | seed-mean D16 at recovery ×1, ×0.25, ×0.1, frozen | strictly increasing across the four | any non-increase | efficacy 0.126 → 0.494 → 0.624 → 0.728 (P1) |
| SR1-std (b) | seed-median half-decrement point, same four | non-decreasing, and frozen > ×1 | any decrease, or frozen ≤ ×1 | efficacy 4 → 6 → 6 → 7 (P1) |
| SR1-std verdict | (a) and (b) | both pass | either fails | — |
| SR1-hebb_only (null) | per-seed D16(scale) − D16(×1), for ×0.25, ×0.1, frozen | every 95 % t-CI contains 0 **and** every \|mean\| < 0.05, **and** the seed-median half point identical across all four | any of those broken | recovery over 48 s < 1.3 % (P3) |
| SR3-std | per-seed R9(insert)/R9(unperturbed) − 1, for +10 and +20 dB | 95 % t-CI upper bound < 0 for **both** inserts | either CI upper ≥ 0 | efficacy −0.21 %, −0.33 % (P5); effect size reported whatever the verdict |
| SR3-hebb_only | same | same | same | direction only (P5) |
| SR2 | slope (dB/decade) over 0.03–0.3 Hz (primary), 0.1–1 Hz (secondary), per arm and schedule | **none — measurement only** | — | +28.7 / +19.8 (`std`, efficacy); ≈ 0 or negative (`hebb_only`) |

Reported with no pass/fail:

- SR1 retention and recognition at 30 min;
- SR2's D at every rate, including 0.01 Hz;
- the implied stage count (slope / 20);
- every control.

## 4. Falsifiers
This line of work (the depression cascade as a model of Stentor-like habituation dynamics) is weakened enough to
close if either of these happens:

- **SR1-std fails** in the network, although the analytic cascade predicts a pass. The cascade's dynamics would then
  not survive the spiking network.
- **SR3-std shows dishabituation** (response at 9 higher after a loud insert, CI lower bound > 0).

A failed SR1-hebb_only null means the long-term rule acts on the training timescale, which contradicts its stated
1 h recovery. That points at a model defect rather than closing the line.

## 5. Model specification
`neurotape.habituation` at `model-v0.1.0`. Full parameter provenance: `ASSUMPTIONS.md` § *Minimal habituation
model*. Summary:

- Relay spikes, Poisson at the per-CF relay rate: spontaneous 1 Hz, max 150 Hz, driven = (pooled Zilany-AN rate −
  its spontaneous rate) / 250 Hz.
  - Zilany, Bruce & Carney 2014, *JASA* 135:283 [LIT] (package run; paper [BG]; no DOI given here because none was checked).
  - Relay mapping [ARBITRARY].
- Relay→E efficacy = U·xf·xs·L. On each relay spike: xf −= U·xf and xs −= a·(release).
  - Recovery: xf by τ_fast; xs by τ_slow; L toward 1 by τ_L.
  - U = 0.5 [ARBITRARY]; τ_fast = 0.8 s [LIT: 10.1073/pnas.94.2.719, ~1 s]; a = 0.05 [ARBITRARY];
    τ_slow = 20 s [LIT: 10.1523/JNEUROSCI.1905-04.2004, "tens of seconds", AB].
- `hebb_only`: no xf/xs. L −= η·release·post·L, with η = 0.0125 (×¼ of the value set by the engagement criterion)
  [DERIVED from the step-2 sweep]; τ_L = 3600 s [ARBITRARY]; post trace τ 100 ms [ARBITRARY].
- LIF E/I cells: C 200/100 pF, gL 10 nS, EL −70, VT −50, Vr −60 mV, τe 5 ms, τi 10 ms, 3 mV noise [BG textbook].
  - I0 = 80 pA and w_in = 8 nS [DERIVED from the operating-point scan against firing-rate criteria only].
  - E→I p 0.2 × 2 nS; I→E p 0.3 × 4 nS [ARBITRARY].
- 200 E / 50 I, 32 CF × 8 relay units, dt 0.5 ms. Silences beyond 2 s are fast-forwarded in mean field (tested
  against direct simulation).
- NM/salience off.

**Sensitivity rule.** Any [ARBITRARY] parameter the verdict turns out to depend on invalidates a pass. The relevant
ones here are U, a and the relay mapping; RESULTS §4 must address them.

## 6. Design
- **Seeds:** 0–9. Each seed is one network *and* one stimulus family (stored sound + 20 novel, 0.2 s, synthetic).
- **Arms:**
  - `std` (depression on, long-term off);
  - `hebb_only` (depression off, anti-Hebbian long-term, η 0.0125);
  - `none` (no depression, no long-term: the plasticity-off control).
- **SR1** (all arms; `none` at ×1 only).
  - 16 presentations of the stored sound, 60 dB, ISI 3 s.
  - The recovery scale is applied at training onset, to the trained network *and* to its control.
  - Then 1800 s, then probes: the stored sound and 20 novel sounds (0.2 s + 0.3 s tail), each to its own copy of
    the trained network and of the control.
  - The control is the naive network carried the same total time (48 s + 1800 s) under the same scale, with
    identical probe spikes and noise.
  - Retention = S(stored) = 1 − R_trained/R_control. Recognition = S(stored) − mean S(novel).
  - Floor rule: a control response below 2 × its expected spontaneous count is "floor" and excluded from retention.
- **SR2** (all arms). Rates 0.01, 0.03, 0.1, 0.3, 1, 3 Hz; 16 presentations of the 0.2 s stored sound.
  - Schedules: periodic, and shuffled (same count and total span; onset spacings uniformly random, Dirichlet, each ≥ 0.2 s).
  - D = 1 − mean(R13..16)/R1.
  - Slope = least squares on 20 log10(seed-mean D) vs log10 rate. 95 % CI = seed bootstrap, 2000 resamples,
    generator seed 0.
- **SR3** (all arms). 16 presentations at 60 dB, ISI 3 s. Presentation 8 is replaced by the stored sound at +10 dB,
  at +20 dB, by silence of equal duration (gap control), or left alone (unperturbed).
  - All four series share identical random draws, so they are paired.
  - Effect = R9/R9(unperturbed) − 1.
- **Exclusions:**
  - A failed run is listed, not dropped.
  - A seed with R1 ≤ 0 has undefined D and D16. It is listed and excluded from those metrics only.
  - Floor seeds are handled as above.
- **Plumbing check before this file.** Each worker ran once on a throwaway smoke configuration (rate periphery,
  60 E cells, 1 seed, 3 rates). Only its success flags and timing were read. It found a NaN in the fast-forward
  under frozen recovery, fixed before `model-v0.1.0` (commit 7b14028).

## 7. Environment
- Python 3.11.16 (uv-managed CPython), macOS 26.5, arm64 (Apple silicon, 10 cores, 16 GB).
- `ENV.lock` sha256: `d3f81994cb32cedb5d54675935c6f98f94f6f4eec2748deb8c9fde5bffe57e20`.
- Execution target: pure numpy (`neurotape.habituation`); **Brian2 is not used**.
- BLAS: OpenBLAS (openblas64, numpy 1.26 wheel), 1 thread per process.
- 8 worker processes (spawn). PYTHONHASHSEED is irrelevant: no hash-ordered code path.
- The same seed on another BLAS or architecture is not claimed to give the same bytes.

## 8. Adaptive stages (optional)
None. SR1, SR2 and SR3 are run once each as specified; no stage's design depends on another's output.

## 9. Open decisions
Decided by the operator (2026-09-24), used as given:

1. `hebb_only` uses η_hebb ×¼ (0.0125).
2. SR1 primary arm = `std` (two-pool cascade). Secondary = `hebb_only` with the 1 h recovery scaled ×0.25, ×0.1 and
   frozen, pre-registered as a predicted null.
3. Half-decrement = first n with R_n ≤ R1 − ½(R1 − R16); absolute halving reported too.
4. Retention = suppression of the stored sound against a time-matched control; recognition beside it.
5. A 0.2 s stimulus at every rate; SR results do not transfer to the 1.5 s stimuli of steps 1–2.
6. SR2 on both `std` and `hebb_only`.
7. SR2's slope is a measurement, not a pass/fail match.
   - Primary window 0.03–0.3 Hz, secondary 0.1–1 Hz.
   - Analytic predictions +28.7 / +19.8 dB/decade; sign convention in P4.
   - **OPEN ITEM:** the sign of Stentor's −30 dB/decade against this model's convention cannot be settled without
     the Escobedo et al. 2026 full text. The comparison is reported as a magnitude and flagged unresolved.
8. SR2 shuffled control as in §6.
9. SR3 on `std` and `hebb_only`: 60 dB base, 70/80 dB inserts, a silent-gap control, the plasticity-off arm,
   salience off.

Decided here, before any output (each forced by the spec):

10. **0.01 Hz is dropped from SR2's fits, and presentations there are not extended.** Its predicted D is 4 × 10⁻⁵,
    because the pools recover fully in the 100 s between onsets. More presentations cannot raise it: the steady
    state is reached after one. It is still run and reported.
11. **The SR1 recovery change applies from training onset** (a resynthesis block given before training) and to the
    control as well (treatment-matched). The control is time-matched over training + delay (1848 s), not only the
    delay, because with a slowed recovery the naive state is no longer stationary.
12. **"Monotone" for SR1-std:** D16 seed means strictly increasing; half-point medians non-decreasing with frozen >
    ×1 (the analytic prediction ties ×0.25 and ×0.1).
13. **SR1-hebb_only "no change":** an equivalence margin of |ΔD16| < 0.05 plus CIs containing 0, and identical median
    half points.
14. **Response window** = the 0.2 s presentation minus expected spontaneous spikes; the SR1 probe window = 0.2 s +
    0.3 s tail.
15. **SR1 floor rule:** a control response below 2 × expected spontaneous = floor, excluded from retention.
16. **SR1 and SR3 use ISI 3 s** (the steps-1–2 standard) with the 0.2 s stimulus.
17. **SR3 pass needs both inserts** (+10 and +20) to deepen, per arm; the verdict is given separately for `std` and
    `hebb_only`.
18. **The plasticity-off arm is `none`,** run in SR1 (×1 only), SR2 and SR3.
19. **Delays over 2 s are fast-forwarded** (mean field for the pools and L; the Hebbian erosion factor is measured
    per run by 10 s of direct simulation).

## 10. Timestamp / archive
**None yet — local git date only, which is not tamper-evident.**

- This repo has no GitHub remote, and there is no GitHub CLI on this machine. So the `-prereg` tag receipt could not
  be posted to a PR, and the tag has not been pushed.
- The receipt is posted to the PR, and its URL recorded in `DEVIATIONS.md`, once the remote exists (no edit here
  after the tag).
- Receipt fields at tagging: the tag commit, the PREREG.md sha256 and the ENV.lock sha256.
- ENV.lock sha256 at tagging: `d3f81994cb32cedb5d54675935c6f98f94f6f4eec2748deb8c9fde5bffe57e20`.
