# REPORT — can the neurotape harness store and recall anything? Luboeinski & Tetzlaff 2021 as the target

Written 2026-09-22 from the runs in `runs/` (every seed, including any failure, is in the JSON). Target and criteria:
[`TARGET.md`](TARGET.md), fixed before any scored run. Differences and every open decision, dated: [`DIFFERENCES.md`](DIFFERENCES.md).
Reference build: [`reference_build/`](reference_build/README.md). Regenerate the tables with `docs/repro/make_report.py`.
No audio anywhere in this task; every stimulus is a direct current into the assembly, as in the paper.

## The answer in four lines

1. **The authors' reference reproduces the paper** (R1): all three pre-registered criteria pass. So "reproduction" means the paper's numbers.
2. **neurotape as-is does not recall** (R2): Q = 0.0004 at 10 s, 0.0065 at 8 h, against the paper's 0.030 / 0.035 — and it is not because
   the assembly failed to form. Every within-assembly synapse is tagged, potentiated and consolidated; the network is simply silent at rest
   (0.001 Hz against the paper's ≈ 1 Hz), so a cue to half the assembly does not spread to the other half.
3. **One difference carries it: the neuron model.** Of nine single removals, only putting the paper's leaky integrate-and-fire cell in place of
   neurotape's conductance-based AdEx cell — with **neurotape's own plasticity and tagging-and-capture code unchanged** — recovers recall
   (Q 0.0385 → 0.0774, MI 0.90 → 1.00, non-cued assembly above a control assembly in 10/10 seeds at both delays, improvement in the paper's
   direction). Removing anything else changes nothing.
4. **It over-recalls rather than under-recalls.** With every listed difference removed (the "paper configuration"), Q is 0.044 → 0.065 against
   the paper's 0.030 → 0.035, so criterion (a) fails on magnitude at both delays — in the *stronger* direction, with a 4–5× wider spread —
   while (b) and (c) pass. The remaining gap is a background rate of 0.28 Hz against the reference's 1.03 Hz; it was not chased.

**So the harness's storage-and-recall machinery — calcium early phase, tags, protein, late phase, in `plasticity/stc.py` — can store and
recall a cell assembly.** The AdEx + T-current cell that neurotape wraps around it cannot, at these parameters, and that cell is what every
neurotape result to date (the tape experiments, the recall drive, the storage diagnostics) was run on.

## R1 — the reference implementation, unmodified, 10 trials

| | ν_as (Hz) | ν_ans (Hz) | ν_ctrl (Hz) | Q (authors' code) | Q (true counts) | MI (bits) | ν_ans > control assembly |
|---|---|---|---|---|---|---|---|
| paper, 10 s | 94.59 | 10.56 | 7.70 | 0.0303 ± 0.0029 | — | 0.8742 ± 0.0346 | — |
| **reference, 10 s** | 94.56 | 10.52 | 7.71 | **0.0298 ± 0.0015** | 0.0290 ± 0.0010 | **0.8851 ± 0.0416** | 10/10 |
| paper, 8 h | 94.71 | 12.41 | 9.10 | 0.0349 ± 0.0037 | — | 0.9759 ± 0.0231 | — |
| **reference, 8 h** | 94.74 | 12.37 | 9.07 | **0.0348 ± 0.0035** | 0.0346 ± 0.0034 | **0.9705 ± 0.0447** | 10/10 |

(a) all four means inside the paper's ±1 SD — **pass**; (b) 10/10 at both delays — **pass**; (c) gain Q **+17 %**, MI **+10 %** (paper +15 %, +12 %) — **pass**.
neurotape's re-implementation of the metrics gives MI identical to 16 digits and Q identical up to the reference's read-out defect (below).
Reference standby E rate 1.03 Hz (its own log).

**Two things found in the reference, neither changing its verdict.** (i) Its rate read-out counts the first in-window spike of every active
cell twice, so every ν and Q in the paper's source data is one spike (2 Hz) high per active cell — a relabelling, so MI is untouched and Q
is ~3 % high. R2's "reference read-out" column applies the same count so the comparison is like for like; the true-count Q is beside it.
(ii) The recall cue in this build goes to the *first* 75 assembly cells, not a random 75 as the Methods say (the random draw belongs to other
build configurations); irrelevant for a random network.

## R2 — main conditions, both delays

| condition | delay | seeds ok | ν_as (Hz) | ν_ans (Hz) | ν_ctrl (Hz) | Q, reference read-out | Q, true counts | MI (bits) | ν_ans > control assembly | standby E rate (Hz) |
|---|---|---|---|---|---|---|---|---|---|---|
| *paper* | 10s | 10 | 94.6 | 10.56 | 7.70 | 0.0303 ± 0.0029 | — | 0.8742 ± 0.0346 | — | 0.5–1.0 (text) |
| *paper* | 8h | 10 | 94.7 | 12.41 | 9.10 | 0.0349 ± 0.0037 | — | 0.9759 ± 0.0231 | — | 0.5–1.0 (text) |
| R2 as-is | 10s | 10/10 | 100.0 ± 0.0 | 0.77 ± 0.25 | 0.74 ± 0.20 | 0.0004 ± 0.0018 | 0.0002 ± 0.0009 | 0.2387 ± 0.0073 | 7/10 | 0.001 ± 0.000 |
| R2 as-is | 8h | 10/10 | 100.0 ± 0.0 | 0.87 ± 0.19 | 0.54 ± 0.12 | 0.0065 ± 0.0030 | 0.0033 ± 0.0016 | 0.2487 ± 0.0145 | 9/10 | 0.001 ± 0.000 |
| remove `lif` only | 10s | 10/10 | 100.9 ± 0.3 | 10.06 ± 1.49 | 6.24 ± 0.58 | 0.0385 ± 0.0131 | 0.0379 ± 0.0133 | 0.8963 ± 0.0572 | 10/10 | 0.276 ± 0.008 |
| remove `lif` only | 8h | 10/10 | 101.6 ± 0.6 | 14.67 ± 2.41 | 6.88 ± 0.85 | 0.0774 ± 0.0215 | 0.0766 ± 0.0216 | 0.9972 ± 0.0720 | 10/10 | 0.276 ± 0.008 |
| remove `fast_forward` only | 10s | 10/10 | 100.0 ± 0.0 | 0.78 ± 0.26 | 0.77 ± 0.21 | 0.0001 ± 0.0018 | 0.0001 ± 0.0009 | 0.2404 ± 0.0080 | 5/10 | 0.001 ± 0.000 |
| remove `fast_forward` only | 8h | 10/10 | 100.0 ± 0.0 | 0.89 ± 0.26 | 0.50 ± 0.14 | 0.0076 ± 0.0027 | 0.0039 ± 0.0014 | 0.2453 ± 0.0055 | 10/10 | 0.001 ± 0.000 |
| remove `lif`+`fast_forward` | 10s | 10/10 | 100.8 ± 0.2 | 10.96 ± 1.31 | 6.58 ± 0.66 | 0.0441 ± 0.0144 | 0.0434 ± 0.0141 | 0.9227 ± 0.0647 | 10/10 | 0.276 ± 0.008 |
| remove `lif`+`fast_forward` | 8h | 10/10 | 101.6 ± 0.6 | 14.78 ± 2.28 | 6.95 ± 0.87 | 0.0781 ± 0.0200 | 0.0771 ± 0.0202 | 1.0016 ± 0.0673 | 10/10 | 0.276 ± 0.008 |
| **paper configuration** (all removed) | 10s | 10/10 | 100.9 ± 0.2 | 11.02 ± 1.76 | 6.65 ± 0.90 | 0.0437 ± 0.0139 | 0.0433 ± 0.0140 | 0.9303 ± 0.0917 | 10/10 | 0.281 ± 0.010 |
| **paper configuration** (all removed) | 8h | 10/10 | 101.7 ± 0.5 | 14.87 ± 1.86 | 8.25 ± 0.66 | 0.0647 ± 0.0161 | 0.0651 ± 0.0164 | 1.0223 ± 0.0668 | 10/10 | 0.281 ± 0.010 |

## R2 — the difference ladder at the 10 s delay (one removal per row)

| condition | delay | seeds ok | ν_as (Hz) | ν_ans (Hz) | ν_ctrl (Hz) | Q, reference read-out | Q, true counts | MI (bits) | ν_ans > control assembly | standby E rate (Hz) |
|---|---|---|---|---|---|---|---|---|---|---|
| *paper* | 10s | 10 | 94.6 | 10.56 | 7.70 | 0.0303 ± 0.0029 | — | 0.8742 ± 0.0346 | — | 0.5–1.0 (text) |
| remove `adaptation` | 10s | 10/10 | 100.0 ± 0.0 | 0.83 ± 0.24 | 0.81 ± 0.21 | 0.0003 ± 0.0016 | 0.0001 ± 0.0008 | 0.2436 ± 0.0115 | 6/10 | 0.011 ± 0.002 |
| remove `t_current` | 10s | 10/10 | 100.0 ± 0.0 | 0.57 ± 0.18 | 0.52 ± 0.16 | 0.0010 ± 0.0016 | 0.0005 ± 0.0008 | 0.1901 ± 0.0074 | 8/10 | 0.000 ± 0.000 |
| remove `gaba_b` | 10s | 10/10 | 104.3 ± 4.3 | 3.14 ± 0.83 | 2.68 ± 0.37 | 0.0047 ± 0.0059 | 0.0044 ± 0.0058 | 0.5820 ± 0.0563 | 8/10 | 0.006 ± 0.001 |
| remove `gap` | 10s | 10/10 | 100.0 ± 0.0 | 0.57 ± 0.23 | 0.50 ± 0.20 | 0.0013 ± 0.0013 | 0.0007 ± 0.0006 | 0.2312 ± 0.0099 | 10/10 | 0.000 ± 0.000 |
| remove `slow` | 10s | 10/10 | 100.0 ± 0.0 | 0.91 ± 0.11 | 0.93 ± 0.05 | -0.0003 ± 0.0022 | -0.0002 ± 0.0011 | 0.2516 ± 0.0111 | 5/10 | 0.001 ± 0.000 |
| remove `theta_pro` | 10s | 10/10 | 100.0 ± 0.0 | 0.77 ± 0.25 | 0.75 ± 0.21 | 0.0004 ± 0.0017 | 0.0002 ± 0.0009 | 0.2379 ± 0.0071 | 7/10 | 0.001 ± 0.000 |
| remove `pl_clock` | 10s | 10/10 | 100.0 ± 0.0 | 0.80 ± 0.25 | 0.78 ± 0.20 | 0.0005 ± 0.0017 | 0.0003 ± 0.0008 | 0.2405 ± 0.0108 | 6/10 | 0.001 ± 0.000 |
| remove `inhibition` | 10s | 10/10 | 100.0 ± 0.0 | 0.90 ± 0.29 | 0.82 ± 0.20 | 0.0009 ± 0.0017 | 0.0008 ± 0.0011 | 0.2676 ± 0.0170 | 8/10 | 0.001 ± 0.000 |
| remove `fast_forward` | 10s | 10/10 | 100.0 ± 0.0 | 0.78 ± 0.26 | 0.77 ± 0.21 | 0.0001 ± 0.0018 | 0.0001 ± 0.0009 | 0.2404 ± 0.0080 | 5/10 | 0.001 ± 0.000 |
| remove `lif` | 10s | 10/10 | 100.9 ± 0.3 | 10.06 ± 1.49 | 6.24 ± 0.58 | 0.0385 ± 0.0131 | 0.0379 ± 0.0133 | 0.8963 ± 0.0572 | 10/10 | 0.276 ± 0.008 |
| remove `lif+theta_pro` | 10s | 10/10 | 100.8 ± 0.2 | 10.02 ± 1.41 | 6.12 ± 0.73 | 0.0395 ± 0.0136 | 0.0386 ± 0.0134 | 0.8950 ± 0.0745 | 10/10 | 0.276 ± 0.008 |
| remove `lif+pl_clock` | 10s | 10/10 | 100.9 ± 0.2 | 10.44 ± 1.43 | 6.42 ± 0.80 | 0.0403 ± 0.0138 | 0.0398 ± 0.0137 | 0.9162 ± 0.0817 | 10/10 | 0.281 ± 0.010 |
| remove `lif+fast_forward` | 10s | 10/10 | 100.8 ± 0.2 | 10.96 ± 1.31 | 6.58 ± 0.66 | 0.0441 ± 0.0144 | 0.0434 ± 0.0141 | 0.9227 ± 0.0647 | 10/10 | 0.276 ± 0.008 |

## R3 — controls

| condition | delay | seeds ok | ν_as (Hz) | ν_ans (Hz) | ν_ctrl (Hz) | Q, reference read-out | Q, true counts | MI (bits) | ν_ans > control assembly | standby E rate (Hz) |
|---|---|---|---|---|---|---|---|---|---|---|
| *paper* | 10s | 10 | 94.6 | 10.56 | 7.70 | 0.0303 ± 0.0029 | — | 0.8742 ± 0.0346 | — | 0.5–1.0 (text) |
| *paper* | 8h | 10 | 94.7 | 12.41 | 9.10 | 0.0349 ± 0.0037 | — | 0.9759 ± 0.0231 | — | 0.5–1.0 (text) |
| as-is, plasticity off | 10s | 10/10 | 100.0 ± 0.0 | 0.11 ± 0.09 | 0.08 ± 0.05 | 0.0005 ± 0.0009 | 0.0003 ± 0.0005 | 0.2025 ± 0.0123 | 5/10 | 0.001 ± 0.000 |
| as-is, shuffled cue | 10s | 10/10 | 100.0 ± 0.0 | 0.45 ± 0.17 | 0.09 ± 0.05 | 0.0070 ± 0.0025 | 0.0035 ± 0.0013 | 0.0328 ± 0.0086 | 10/10 | 0.001 ± 0.000 |
| paper config, plasticity off | 10s | 10/10 | 100.2 ± 0.1 | 1.54 ± 0.32 | 1.60 ± 0.22 | -0.0005 ± 0.0032 | -0.0006 ± 0.0031 | 0.2986 ± 0.0155 | 5/10 | 0.281 ± 0.010 |
| paper config, plasticity off | 8h | 10/10 | 100.2 ± 0.1 | 1.51 ± 0.39 | 1.56 ± 0.24 | -0.0006 ± 0.0045 | -0.0005 ± 0.0037 | 0.2980 ± 0.0195 | 3/10 | 0.281 ± 0.010 |
| paper config, shuffled cue | 10s | 10/10 | 100.4 ± 0.1 | 5.06 ± 0.75 | 1.96 ± 0.23 | 0.0343 ± 0.0074 | 0.0308 ± 0.0077 | 0.2515 ± 0.0177 | 10/10 | 0.279 ± 0.009 |
| paper config, shuffled cue | 8h | 10/10 | 100.4 ± 0.1 | 5.14 ± 0.98 | 2.00 ± 0.23 | 0.0352 ± 0.0090 | 0.0313 ± 0.0089 | 0.2702 ± 0.0248 | 10/10 | 0.279 ± 0.009 |

## Criteria

### R2 as-is

| criterion | value | target | result |
|---|---|---|---|
| (a) Q(10 s) | 0.0004 ± 0.0018 (n = 10) | [0.0274, 0.0332] | **FAIL** |
| (a) Q(8 h) | 0.0065 ± 0.0030 (n = 10) | [0.0312, 0.0386] | **FAIL** |
| (a) MI(10 s) | 0.2387 ± 0.0073 (n = 10) | [0.8396, 0.9088] | **FAIL** |
| (a) MI(8 h) | 0.2487 ± 0.0145 (n = 10) | [0.9528, 0.9990] | **FAIL** |
| (b) ν_ans > control assembly, 10s | 7 of 10 seeds | ≥ 8 | **FAIL** |
| (b) ν_ans > control assembly, 8h | 9 of 10 seeds | ≥ 8 | **pass** |
| (c) improvement | Q +1379.6%, MI +4.2% | both > 0 (paper +15 %, +12 %) | **pass** |

**(a) **FAIL** · (b) **FAIL** · (c) **pass****

### remove `lif` only

| criterion | value | target | result |
|---|---|---|---|
| (a) Q(10 s) | 0.0385 ± 0.0131 (n = 10) | [0.0274, 0.0332] | **FAIL** |
| (a) Q(8 h) | 0.0774 ± 0.0215 (n = 10) | [0.0312, 0.0386] | **FAIL** |
| (a) MI(10 s) | 0.8963 ± 0.0572 (n = 10) | [0.8396, 0.9088] | **pass** |
| (a) MI(8 h) | 0.9972 ± 0.0720 (n = 10) | [0.9528, 0.9990] | **pass** |
| (b) ν_ans > control assembly, 10s | 10 of 10 seeds | ≥ 8 | **pass** |
| (b) ν_ans > control assembly, 8h | 10 of 10 seeds | ≥ 8 | **pass** |
| (c) improvement | Q +101.1%, MI +11.3% | both > 0 (paper +15 %, +12 %) | **pass** |

**(a) **FAIL** · (b) **pass** · (c) **pass****

### **paper configuration** (all removed)

| criterion | value | target | result |
|---|---|---|---|
| (a) Q(10 s) | 0.0437 ± 0.0139 (n = 10) | [0.0274, 0.0332] | **FAIL** |
| (a) Q(8 h) | 0.0647 ± 0.0161 (n = 10) | [0.0312, 0.0386] | **FAIL** |
| (a) MI(10 s) | 0.9303 ± 0.0917 (n = 10) | [0.8396, 0.9088] | **FAIL** |
| (a) MI(8 h) | 1.0223 ± 0.0668 (n = 10) | [0.9528, 0.9990] | **FAIL** |
| (b) ν_ans > control assembly, 10s | 10 of 10 seeds | ≥ 8 | **pass** |
| (b) ν_ans > control assembly, 8h | 10 of 10 seeds | ≥ 8 | **pass** |
| (c) improvement | Q +48.1%, MI +9.9% | both > 0 (paper +15 %, +12 %) | **pass** |

**(a) **FAIL** · (b) **pass** · (c) **pass****


## Tag counts (D2-style), mean over 10 seeds

### as-is

| delay run | instant | within assembly: tags pot / dep | late-phase pot / dep | mean h / z | outside assembly: tags pot / dep | late-phase pot / dep | protein: assembly / rest |
|---|---|---|---|---|---|---|---|
| 10s | pre_learning | 0 / 0 of 2226 | 0 / 0 | 1.000 / 0.000 | 0 / 0 of 253476 | 0 / 0 | 0.000 / 0.000 |
| 10s | end_of_learning | 2226 / 0 of 2226 | 0 / 0 | 1.696 / 0.001 | 43473 / 0 of 253476 | 0 / 0 | 0.031 / 0.016 |
| 10s | pre_10s_recall | 2226 / 0 of 2226 | 2226 / 0 | 1.649 / 0.013 | 43473 / 0 of 253476 | 39874 / 0 | 0.152 / 0.111 |
| 8h | pre_learning | 0 / 0 of 2226 | 0 / 0 | 1.000 / 0.000 | 0 / 0 of 253476 | 0 / 0 | 0.000 / 0.000 |
| 8h | end_of_learning | 2226 / 0 of 2226 | 0 / 0 | 1.696 / 0.001 | 43473 / 0 of 253476 | 0 / 0 | 0.031 / 0.016 |
| 8h | pre_10s_recall | 2226 / 0 of 2226 | 2226 / 0 | 1.649 / 0.013 | 43473 / 0 of 253476 | 39874 / 0 | 0.152 / 0.111 |
| 8h | pre_8h_recall | 0 / 0 of 2226 | 2226 / 0 | 1.010 / 0.778 | 0 / 0 of 253476 | 40809 / 0 | 0.014 / 0.000 |

### paper configuration

| delay run | instant | within assembly: tags pot / dep | late-phase pot / dep | mean h / z | outside assembly: tags pot / dep | late-phase pot / dep | protein: assembly / rest |
|---|---|---|---|---|---|---|---|
| 10s | pre_learning | 0 / 0 of 2229 | 0 / 0 | 1.000 / 0.000 | 0 / 0 of 253472 | 0 / 0 | 0.000 / 0.000 |
| 10s | end_of_learning | 2229 / 0 of 2229 | 0 / 0 | 1.703 / 0.000 | 54004 / 0 of 253472 | 0 / 0 | 0.001 / 0.001 |
| 10s | pre_10s_recall | 2229 / 0 of 2229 | 0 / 0 | 1.702 / 0.000 | 53995 / 0 of 253472 | 0 / 0 | 0.003 / 0.003 |
| 8h | pre_learning | 0 / 0 of 2229 | 0 / 0 | 1.000 / 0.000 | 0 / 0 of 253472 | 0 / 0 | 0.000 / 0.000 |
| 8h | end_of_learning | 2229 / 0 of 2229 | 0 / 0 | 1.703 / 0.000 | 54004 / 0 of 253472 | 0 / 0 | 0.001 / 0.001 |
| 8h | pre_10s_recall | 2229 / 0 of 2229 | 0 / 0 | 1.702 / 0.000 | 53995 / 0 of 253472 | 0 / 0 | 0.003 / 0.003 |
| 8h | pre_8h_recall | 0 / 0 of 2229 | 2229 / 0 | 1.011 / 0.775 | 0 / 0 of 253472 | 53364 / 0 | 1.000 / 0.228 |


## What the tables say

- **Assemblies form under the paper's stimulus in every configuration with plasticity on.** With the current (Luboeinski & Tetzlaff)
  parameters — the ones that passed 1 of 5 slice protocols in P1 — the 0.1 s pulses at ~500 Hz drive every one of the ~2230 within-assembly
  synapses over θ_p: 100 % tagged for potentiation, 0 for depression, mean h 1.70 h₀ at the end of learning, and by 8 h the late phase carries
  the weight (z 0.78, h back to 1.01). Outside the assembly ~54 000 synapses (21 %) potentiate too — more than the 43 500 that touch an
  assembly cell at all, so some control→control ones as well — the paper's own observation that non-stimulated synapses also change and
  that weights *into* the assembly grow. This is the opposite of what the D4 tape runs wrote (depression only): a 500 Hz drive is not a
  10 Hz auditory-nerve drive.
- **Protein and late phase behave differently in as-is and paper configurations, and it does not matter for recall.** As-is (θ_pro = 8.3 h₀,
  60× compression) has protein at 0.15 by the 10 s cue and late-phase on every tagged synapse already; the paper configuration (θ_pro = 0.5 h₀,
  real time) has p ≈ 0.003 at 10 s and reaches p = 1.0 in the assembly by 8 h with z 0.78 — the paper's Fig 6 picture. Both consolidate.
  Neither consolidation nor its timing is what separates recall from no recall: the 10 s ladder shows that.
- **Recall is decided by the cell, not the synapse.** Every AdEx-based rung leaves the network at ≤ 0.011 Hz in standby and ν_ans within
  0.1 Hz of ν_ctrl; the LIF-based rungs sit at 0.28 Hz and give ν_ans ≈ 1.6 × ν_ctrl. The GABA_B removal is the one AdEx rung that moves
  anything (standby 0.006, MI 0.58) and still gives Q 0.005.
- **The over-recall.** In the paper configuration ν_ans is 11.0 / 14.9 Hz against the paper's 10.6 / 12.4 and ν_ctrl 6.7 / 8.3 against
  7.7 / 9.1. Lower background (0.28 vs 1.03 Hz) means less control activity in the read-out window and a larger numerator. Remaining
  unremoved differences: Heun integration instead of the reference's exact exponential steps; Brian2's noise generator; a new random network
  per seed rather than the authors' one fixed structure; cells firing at exactly 500 Hz rather than ~470. The spread is also 4–5× the
  paper's (Q SD 0.014 vs 0.003), which a single fixed network would be expected to narrow. None of this was tuned.

## R3 — controls

- **Plasticity off** (both configurations, both delays): Q −0.0006 … +0.0005, ν_ans within 0.1 Hz of the control assembly, (b) 3–5/10 —
  chance. Recall in the paper configuration is the plasticity's doing. MI 0.30 with plasticity off against 0.93 with it on.
- **Shuffled cue** (75 never-learned cells cued; ν_ans is then the whole 150-cell stored assembly): with the **as-is** model the stored
  assembly barely stirs (0.45 Hz vs 0.09 control, MI 0.03). With the **paper configuration** it does respond: **5.1 Hz against 2.0 Hz for
  control cells, in 10/10 seeds, Q 0.034**, though the recall *pattern* is not the learned one (MI 0.25 against 0.93 with the true cue).
  So the spec's expectation — "recall of the stored assembly should not occur" — is **not met in the strict sense**: a consolidated assembly is
  more excitable than the rest of the network to *any* excitation, because synapses from control cells onto it were potentiated too. The paper reports the same incoming-weight growth (its Fig 3b, c). Pattern completion proper — the specific 75 lighting
  up the other 75 — still separates cleanly: ν_ans 11.0 Hz with the true cue against 5.1 with a shuffled one, MI 0.93 against 0.25.

## Not done, and stated

- The `lif` rung was not run with only *one* of `theta_pro` / `pl_clock` / `fast_forward` at **8 h** (only at 10 s, where none moves the
  result); the 8 h combinations run were `lif`, `lif+fast_forward` and the full paper configuration.
- No attempt was made to close the standby-rate gap (0.28 vs 1.03 Hz) or the variance gap; doing so would be tuning.
- The reference was not run with a shuffled cue or with plasticity off; R3 is about the harness, as specified.
- MI's discretisation follows the authors' code (plug-in entropy over exact spike counts); the paper does not state it.
- Wall time: reference 7–14 min per 10 s trial, ~5 min per fast-forwarded 8 h trial; neurotape 3.5 min per 10 s run, 76 min per
  compressed 8 h run, 8–19 min per analytic-fast-forward 8 h run. Total simulation ≈ 30 machine-hours across 270 runs, 0 failed.
