# TARGET — Luboeinski & Tetzlaff 2021, as the reproduction target

Luboeinski J, Tetzlaff C. *Memory consolidation and improvement by synaptic tagging and capture in recurrent
neural networks.* Commun Biol 4:275 (2021). doi 10.1038/s42003-021-01778-y · PMC7977149 · CC-BY 4.0.

Written 2026-09-21 **before any scored run**. One build-test run of the reference binary had been made to time
it (7 min 31 s); its metrics were not read and it is excluded from the ten scored trials.

**Read depth.** Main text read **in full** (Introduction, Results, Discussion, Methods, Tables 1–2, figure
legends) through `tools/paper-library`, machine-extracted — equations arrive as LaTeX and were read as such.
**Supplementary Data 1** (the figures' per-trial source data, `42003_2021_1778_MOESM3_ESM.xlsx`) downloaded from
the publisher and parsed: **every numeric target below comes from it**, because the paper's text states no Q or
MI value for the standard network — they are only drawn (Figs 4, 5, 7). Supplementary Information (Figs S1–S7)
skimmed for the standby rate only. Reference code (`jlubo/memory-consolidation-stc`, commit `ac6d2ba`,
Apache-2.0) read where the paper is silent; those items are marked **code only**.

## The model

| item | value | source |
|---|---|---|
| network | 2000 neurons: **1600 E, 400 I** | Results ¶ "Employing our synaptic model…"; Table 1 |
| connectivity | probability **0.1** for every ordered pair, all four projection types | Table 1 (`p_c`); Methods "Network" |
| neuron | **leaky integrate-and-fire**, current-based exponential synapses; τ_mem 10 ms, τ_syn 5 ms, R 10 MΩ, V_rev −65, V_reset −70, V_th −55 mV, t_ref 2 ms, axonal delay 3 ms, Δt 0.2 ms | Table 1, Eq. 8 |
| background | Ornstein–Uhlenbeck current to every neuron, I₀ 0.15 nA, σ_wn 0.05 nA s^½, τ 5 ms | Table 1, Eq. 9 |
| weights | h₀ = 0.420075 nC (4.20075 mV); E→E = h + h₀·z, **plastic**; w_ei = 2 h₀; **w_ie = w_ii = 4 h₀** (the standard setting of Figs 3, 5a–d, 6, 9); only E→E is plastic | Table 1, Eq. 10, Fig 3 legend |
| calcium | c_pre **0.6**, c_post **0.1655** (the *network* values — Table 1's 1 / 0.2758 × 0.6 for in-vivo calcium), τ_c 48.8 ms, pre delay 18.8 ms | Table 2 parentheses; Methods ¶ "The calcium parameters…" |
| early phase | τ_h 688.4 s, γ_p 1645.6, γ_d 313.1, **θ_p 3.0, θ_d 1.2**, ceiling 1 nC (= 2.38 h₀), relaxation 0.1(h₀ − h), σ_pl 0.290436 nC s^½ | Table 2, Eq. 11 |
| tag / capture | θ_tag 0.0840149 nC (0.2 h₀); late phase τ_z 60 min, LTP toward 1, LTD toward −0.5 | Table 2, Eqs. 13–14 |
| protein | per postsynaptic neuron, τ_p 60 min, α 1, synthesis when Σ_j\|h_ji − h₀\| > θ_pro = 0.210037 nC (0.5 h₀) | Table 2, Eq. 15 |
| time | **no time compression.** Between stimuli the reference *fast-forwards*: spiking is skipped and only the h decay, z and p are integrated | Methods, last ¶; Fig S2 |

## The protocol

| step | value | source |
|---|---|---|
| settle | 10.0 s | Methods "Learning and recall procedure" |
| learning stimulus | **three pulses of 0.1 s** at t = 10.0, 10.5, 11.0 s (0.4 s breaks), to the **first 150 E neurons** | same; pulse times **code only** (`StimulusProtocols.cpp`) |
| stimulus form | an OU current, mean w_stim·N_stim·f_stim with **N_stim = 25 putative inputs at f_stim = 100 Hz, w_stim = h₀**, SD w_stim·√(N_stim·f_stim), τ_syn — not spikes. Stimulated cells fire "at their maximum" (≈ 470 Hz) | Eq. 16, Table 1, Results |
| recall cue | the **same** OU stimulus for **0.1 s** to **50 %** of the assembly (75 cells, **randomly drawn** — code only) | Methods; Table 1 `r` |
| delays | **10 s** after learning (cue at t = 20.0 s) and **8 h** (cue at t = 28 810.0 s). The 8 h run restarts from the state saved at t = 20.0 s, so the 10 s cue does **not** precede the 8 h cue | Methods |
| trials | **10** per condition; one fixed connectivity (`connections.txt`), seed = system clock | Methods "Statistics"; code |

## The metrics, exactly as defined

- **Firing rate ν(t, n)**: spikes of neuron n in a **0.5 s window centred on t** (Methods; centring is code only,
  `instFiringRates`). Read at t = 20.1 s and 28 810.1 s — so the window spans the 0.1 s cue and 0.15–0.25 s either side.
- **Pattern completion Q\*** = (ν̄_ans − ν̄_ctrl) / ν̄_as (Eq. 17): `as` = the 75 cued assembly cells, `ans` = the 75
  assembly cells not cued, `ctrl` = the other 1450 E cells. **Q = ⟨Q\*⟩ over trials** (Eq. 20). Memory is called
  functional at **Q ≥ 0.03**.
- **Mutual information MI_ν** = H(ν_learn) + H(ν_recall) − H(ν_learn, ν_recall) over the 1600 E cells' rate
  distributions, ν_learn read at t = 11.0 s (Eq. 19). Discretisation is code only (`analysis/calculateMIa.py`).
- **Relative gain** = (X(8 h) − X(10 s)) / X(10 s) on the trial means.

## Reported values — n_CA = 150, w_ie = w_ii = 4 h₀, mean ± SD over 10 trials

From Supplementary Data 1, sheet "Figure 5a,b,c,d" (the curves of Fig 5a, b):

| delay | ν_as (Hz) | ν_ans (Hz) | ν_ctrl (Hz) | **Q** | [min, max] | **MI (bits)** | [min, max] |
|---|---|---|---|---|---|---|---|
| 10 s | 94.59 | 10.56 | 7.70 | **0.0303 ± 0.0029** | 0.0256 – 0.0347 | **0.8742 ± 0.0346** | 0.806 – 0.916 |
| 8 h | 94.71 | 12.41 | 9.10 | **0.0349 ± 0.0037** | 0.0311 – 0.0406 | **0.9759 ± 0.0231** | 0.935 – 1.013 |

**Late-time improvement at this size: Q +15 %, MI +12 %** (positive at every assembly size in Fig 5c, d). The
paper's headline "> 200 %" and "as much as 30 %" are the maxima over sizes (n_CA = 350: Q 0.0789 → 0.2681).
An independent batch of 10 trials at the same setting (sheet "Figure 4") gives Q 0.0310 ± 0.0031 → 0.0339 ± 0.0019
and MI 0.868 ± 0.034 → 0.957 ± 0.033 — the paper's own batch-to-batch repeatability, well inside one SD.
Not reproduced here: the inhibition sweep (Fig 4), the size sweep (Fig 5), early-phase blocking (Fig 7),
intermediate recall (Fig 9).

Basal activity: 0.5–1.0 Hz mean E rate in standby is *asserted to resemble* hippocampus (Results; Fig S3); the
source data's ν_ctrl of 7.7 Hz is the rate inside the recall window, not standby.

## Pre-registered pass criteria (fixed here, before any scored run; identical for R1 and R2)

**(a) Magnitude.** At each delay, the 10-seed mean of **Q** and of **MI** lies within the paper's reported spread,
taken as **mean ± 1 SD of its ten trials** (the error bar it draws): Q(10 s) ∈ [0.0274, 0.0332], Q(8 h) ∈
[0.0312, 0.0386], MI(10 s) ∈ [0.8396, 0.9088], MI(8 h) ∈ [0.9528, 0.9990]. All four must hold; each is reported
separately. (No ±20 % fallback is needed — a spread is given for every value.)

**(b) Specificity.** In the same run and the same 0.5 s window, the mean rate of the 75 *non-cued assembly cells*
exceeds the mean rate of a **control assembly**: 75 E cells drawn at random (seeded) from cells that were never
stimulated by learning or by the cue. Pass = ν̄_ans > ν̄_control-assembly in **≥ 8 of 10 seeds**, judged at each
delay separately.

**(c) Improvement.** Direction only: **Q(8 h) > Q(10 s)** and **MI(8 h) > MI(10 s)** on the 10-seed means. The
magnitude of each gain is reported beside the paper's +15 % / +12 % and does not enter the criterion.

A run that errors is reported as a failed seed and counts against (b); it is never dropped.

## Corrections after writing (criteria untouched)

- **2026-09-21, while R1 was running.** The recall cue in the paper-1 build goes to the **first 75** assembly cells
  (`setBlockStimulus`), not a random 75 as stated above — the random draw belongs to other build configurations.
  Found by reading which cells fire at ~94 Hz in a reference output file.
- **2026-09-21, from the first five R1 trials.** The reference's rate read-out (`instFiringRates`) counts the first
  in-window spike of every active cell twice, so the rates in its `_net_<t>.txt` files — and therefore **every ν and Q
  in the paper's source data** — read one spike (2 Hz) high for each cell that fired in the window. It is a relabelling
  of counts, so MI is exactly unchanged; Q from true counts is about 3 % lower than Q from the files. Criterion (a)
  compares like with like: R1 is scored from the authors' files with the authors' analysis code; R2 is scored with the
  same read-out applied (`Q_ref_readout`), and its true-count Q is reported beside it.
