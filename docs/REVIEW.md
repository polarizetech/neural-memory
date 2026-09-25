# REVIEW — pre-release code and methods review (2026-09-25)

Three independent reviews were run before this repository went public, each reading the code as a skeptical
computational neuroscientist and engineer. One covered the tape model, one the habituation model, and one the
statistics and reproducibility. Every finding below was checked against the code. Findings that change how a
committed result should be read are also appended, dated, to that result's report. Nothing already published in
a report was rewritten.

## TL;DR

- **No equation, unit or integration error was found** in either model. Checked: the Luboeinski & Tetzlaff STC
  rule, the T-current against ModelDB 3343, AdEx, noise scaling, Euler stability, Tsodyks–Markram order, iSTDP
  against Vogels 2011, and the receptor pools.
- **Five findings change how committed results read.** None flips an experiment's verdict:
  1. The Hebbian factor starts off its resting state.
  2. The tape's rank-order "positive" is an encoding-time readout of the input.
  3. Recall delays are later than labelled.
  4. E02's MDE rule has two readings.
  5. Several reports over-state per-cell results as simultaneous ones.
- **Fixed in code** (no committed number changes): a latent pairing bug, the private-tool imports, the
  blind-exception tests and the lint findings.

## 1. Findings that affect how committed results read

| # | Finding | Where | What it changes | Recorded in |
|---|---|---|---|---|
| R1 | **The Hebbian factor L starts at 1, but spontaneous release × the postsynaptic trace erodes it toward ~0.11 (η 0.05) or ~0.31 (η 0.0125), with time constants of ~6 and ~18 min.** The naive control is not stationary. | `habituation/model.py` (`initial_state`), `protocol.py` (`fast_forward`) | (a) Recognition at 30 min (`docs/habituation`) is set by this erosion, not by τ_s = 1 h. (b) E02's H spaced − massed (−0.20) compares controls at very different strength, so it is **confounded**. B and R start at their true steady states and are not affected. (c) E01 SR2 `hebb_only`'s low-rate slope has no time-matched control and is plausibly an erosion artefact. SR1 is time-matched and not affected. | habituation, E01, E02 RESULTS; FINDINGS |
| R2 | **hab_memory's naive controls are carried through the delay only, not the training time as well.** | `experiments/habituation.py` (`carry(st0, d, …)`) | With R1, both S_stored and S_novel are inflated equally (~13 % efficacy at η 0.05). Recognition, their difference, is protected to first order. | habituation RESULTS |
| R3 | **The tape's rank-order result is a readout of the input during encoding.** Rank is accumulated from `g_ext + g_e` while the stimulus plays, and the feedforward term dominates. No input-only control was run; the permutation null ignores autocorrelation. | `neurons/model.py`, `recall/evaluate.py` | The "one clear positive" shows that cells follow the input, not that the network keeps anything. | tape RESULTS; FINDINGS; CLAUDE.md |
| R4 | **Recall delays are later than labelled**: probe k starts `d_k + k × probe length` after encoding. | `recall/protocol.py` (`build_timeline`) | Recall is at chance everywhere, so no verdict changes; every delay axis is off by up to that amount. | tape RESULTS; FINDINGS |
| R5 | **E02's MDE rule has two readings.** Read literally, P2b ×4 and P4b massed 3600/5400 s become UNINTERPRETABLE. | E02 PREREG §3 vs `analyse.py` | The overall FAIL stands on P4a under either reading. | E02 DEVIATIONS #3, RESULTS |
| R6 | **Per-cell claims read as simultaneous ones.** E02's "no specific retention at any delay or overlap" is uncorrected over 54 cells (the Bonferroni bound is 0.066 > SESOI). E02 §4 over-reaches on robustness. B-vs-H removal was inferred from two CIs, not a contrast. | E02 RESULTS | wording | E02 RESULTS |
| R7 | **E02 arm R, spaced: "the driven response falls below spontaneous"** comes from subtracting the naive spontaneous count. The network actually went nearly silent (~4 spikes in 1.5 s). That subtraction is what makes P4b-spaced undefined. | E02 `run.py` (`_driven`) | wording; P4c stays FAIL on total counts (−0.72 at 5400 s) | E02 RESULTS |
| R8 | **E01's MDE is a CI half-width** (~50 % power), not an 80 %-power MDE; the SR2 bootstrap drops resamples with D ≤ 0. | E01 DEVIATIONS #1, `analyse.py` | No verdict changes; the SR2 control CIs are conditional. | E01 RESULTS |
| R9 | **The echo-state baseline had 250 units, the spiking readout 200.** | `decode/baselines.py` | favours the baseline | FINDINGS |

## 2. Defects that do not affect committed results

| Finding | Where | Status |
|---|---|---|
| `paired_diff` paired by list position and truncated unequal lengths (a failed seed would misalign every later pair; no committed paired condition had one) | `experiments/common.py` | **fixed**: unequal lengths now raise |
| Settle crash for plastic FF inhibition before α is set (cost E02 its B seed 0) | `habituation/model.py` | open (E02 DEVIATIONS #2) |
| `input_plastic` + `freeze_plasticity_at_recall` cannot build (`pl_t` missing from the input namespace) | `network.py` | open; raises, never run |
| The auditory-nerve noise floor raises every relay channel to 5–9 Hz during any sound (clipped noise becomes a positive bias) | `habituation/periphery.py` | open; plausibly adds to E02's generalisation, moves overlap only ~0.04 |
| `fast_forward` decays NM but not the salience filters | `habituation/protocol.py` | open; step 3 is already uninterpretable |
| `efficacy_by_cf` ignores receptor and FF state | `habituation/measure.py` | open; no committed run combines them |
| `theta_pro_default` is unused (`nm_dep` hard-coded); `tau_s` commented "minutes" but used as seconds | `neurons/model.py`, `config.py` | open, cosmetic |
| The cue level is set over the cue segment alone; NM salience is z-scored with whole-window (future) statistics | `frontend/an.py`, `neuromod/nm.py` | open, methodology notes |

## 3. Lint

`ruff` runs with correctness rules only (`pyproject.toml`: pyflakes, bugbear, pylint errors, numpy, datetime,
ruff-specific; no style rules, no formatter). The first run found 79 findings.

| Finding | Action |
|---|---|
| 22 unused imports | removed |
| 13 `zip()` without `strict=` (silent truncation) | `strict=True` where lengths must match, including recall windows against timeline segments; `itertools.pairwise` for successive pairs |
| 8 `pytest.raises(Exception)` | narrowed to pydantic's `ValidationError`, so a typo can no longer pass them |
| 27 closures over loop variables | each read; every one is defined and called within one iteration, so per-file ignores record that |
| 3 unused variables | removed; none was a bug |

The frozen scripts of the two closed experiments are not edited; their findings (pairwise `zip`s, same-iteration
closures) were read and are safe. `ruff check .` is clean, and the test suite passes (100).

## 4. Reproducibility

**What runs with only this repository:**
- the habituation model and its tests;
- both experiments' `analyse.py`, which need only numpy, scipy and pyyaml and read the committed `outputs/`.

That is the recommended way to check E01 and E02.

**What needs more:**
- **`cochlea`** (Zilany 2014; GPL-3, installed from git, builds against Cython < 3): every habituation config uses
  it. The install commands are in the README; the pinned commit is in each experiment's `ENV.lock`.
- **Two tools from a private monorepo:**
  - the provenance stamper, which writes `provenance.json` and changes no number;
  - `uwtl`, the tape model's secondary IAAFT null.
  
  Without them, the tape decoder now skips the IAAFT null and records `p_iaaft: null` with the reason, and the
  monorepo tests skip. The E01/E02 `run.py` scripts call the stamper unguarded; they are frozen and cannot be
  changed, so a stranger re-running them gets `runs.json` and then an error before `SHA256SUMS`.
- **Exact re-runs of E01/E02** also need `git checkout` of the experiment's model tag (the gates refuse a modified
  `src/`) and the macOS arm64 environment in `ENV.lock`. Byte-identical reproduction is claimed only on that
  platform.

## 5. What was checked and found sound

- Decoder: no leakage (standardisation on training data, the penalty chosen inside encoding, applied unchanged to
  recall).
- Nulls: the best-lag nulls search the same lag range as the statistic.
- Tape model: the STC rule after dividing by h₀; T-current kinetics and sign; AdEx; OU noise SD; dt against every
  time constant; rank-window bookkeeping; the offline ΔW predictor.
- Habituation model: Euler stability (max dt·g/C 0.63); units; the noise scaling; the release→deplete→recover
  order; iSTDP; receptor pools; the exact per-second decays; pairing of trained and control networks.
- Statistics: E02's paired design; its TOST implementation; about 20 numbers spot-checked against the outputs, all
  matching.
- Privacy: no credentials, keys or tokens in history. `/Users/<user>` paths remain inside traceback strings in
  frozen outputs and session logs; they are left in place so the committed checksums stay valid.
