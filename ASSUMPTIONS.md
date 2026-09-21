# ASSUMPTIONS — what is published, what is a placeholder, and where every number came from

**Read depth is stated per source.** `READ` = retrieved and read this build (through
`tools/paper-library` or the authors' repository). `MEMORY` = cited from memory and **not** retrieved;
treat the number as unverified until someone reads the source.

## The rule this file enforces

> **No parameter was tuned to make recall look good.** Parameters were set in two passes, both
> finished **before the readout existed**: (1) single-cell parameters, by the single-cell unit
> tests; (2) the network operating point, by firing-rate and mechanism-engagement criteria only.
> This ordering is a statement about the build session, not something git can prove: the whole
> project was written uncommitted in one sitting, so there is no commit separating the two passes.
> What can be checked is that no experiment code reads a recall metric back into a parameter.

### Operating-point criteria (the only thing network-level weights were set against)

| criterion | measured at the frozen point (200 E / 50 I, 6 s encode) |
|---|---|
| E firing is sparse and competitive during encoding | mean 2.2 Hz, median ~0, max 64–83 Hz |
| consolidation is quiet, as in the reference | 0.01 Hz |
| the LOADED state is reachable, so the T-current ablation is not a no-op | 13–17 % of encode time |
| both LTP and LTD tags are set during encoding | tag+ 0.02–1.1 %, tag− 3–5 % of synapses |

Two parameters were moved to satisfy these and nothing else: `mixing.g_in_mean_nS` (4 → 8; at 4 only
LTD occurred) and the GABA_B-like conductance (added; without it LOADED was **0.0000** — see below).

---

## Phenomenological placeholders — mechanisms with no quantitative source

These are the parts a reader should distrust first. Each has a switch.

| placeholder | what it stands for | where | switch |
|---|---|---|---|
| **synaptic tag** | a threshold on early-phase change, `|h − h0| > θ_tag`; no molecular identity | `plasticity/stc.py` | `mechanisms.tagging` |
| **protein pool** `p` | one scalar per neuron, driven when summed early-phase change exceeds `θ_pro(NM)`; shared by all of a cell's synapses | `neurons/model.py` | follows `tagging` |
| **CREB-like variable** | low-pass of somatic calcium over minutes; lowers spike threshold by up to `dVT_mV` | `neurons/model.py` | `mechanisms.creb` |
| T-current calcium → synaptic calcium | `Ca_tot = Ca + c_T·CaT_post`; `c_T`, `k_CaT`, `tau_CaT` are invented | `plasticity/stc.py` | `mechanisms.t_current` |
| salience → phasic NM | z-scored `|env − running mean|` crossing 2 triggers an alpha-function transient | `neuromod/nm.py` | `mechanisms.nm_dynamic` |
| NM → input gain, inhibitory set point | `1 + k_gain(NM − ref)`; bias current `k_inh(NM − ref)` to I cells | `network.py`, `model.py` | `mechanisms.nm_dynamic` |
| attention | NM follows the attended stream's envelope. A **global** modulator cannot be stream-specific; this makes it *temporally* specific instead | `neuromod/nm.py` | `attention.stream` |
| theta pacemaker | an external cosine current; phase reset on envelope onsets is imposed, not emergent | `neuromod/theta.py` | `mechanisms.theta`, `theta.mode` |
| MOC-like efferent | tonic NM lowers cochlear input by `moc_db_per_nm` dB | `frontend/an.py` | `frontend.moc_enabled` (off) |
| pH/Mg gap modulation | one scalar multiplying gap conductance | `coupling/gap.py` | `gap.modulation` |
| MSO stage | a coincidence counter across internal delays, not a membrane model | `frontend/brainstem.py` | `frontend.mso` (off) |
| engram cell | protein pool ever ≥ 0.1 (or mean incoming `z` ≥ 0.1) | `decode/readout.py` | `decode.engram_metric` |
| LFP proxy | weighted sum of synaptic currents; a point network has no geometry | `decode/population.py` | — |

## Time compression (default 60×), printed on every figure

Applied **only** to the hours-scale terms: early-phase decay `0.1(h0 − h)/τ_h`, `τ_p`, `τ_z`, `τ_creb`.
**Not** applied to induction (the `γ_p`, `γ_d` terms and their noise), calcium, membrane or synaptic
dynamics, the OU drift (10 s is a stated value, not an hours-scale process) or NM transients. So a
"delay of 120 s" means 120 s of fast dynamics and 2 h of slow-process time. Consequence that
cannot be removed: background spiking during consolidation happens 60× less often per unit of
slow-process time than it would in a real 2 h. The reference instead fast-forwards analytically
through silent periods; that is not implemented here.

## Parameters and their sources

### Plasticity and STC — Luboeinski & Tetzlaff 2021, *Commun Biol* 4:275, doi:10.1038/s42003-021-01778-y — `READ` (paper held in the library; values read from the authors' `config_defaultnet.json` and `brianNetworkConsolidation.py`)

`Ca_pre 0.6`, `Ca_post 0.1655`, `τ_Ca 48.8 ms`, `t_Ca_delay 18.8 ms`, `θ_p 3.0`, `θ_d 1.2`, `γ_p 1645.6`,
`γ_d 313.1`, `τ_h 688.4 s`, `σ_pl 2.90436 mV`, `h0 4.20075 mV`, `h_max 10 mV`, `θ_tag 0.840149 mV`,
`θ_pro 2.10037 mV`, `α 1`, `τ_p = τ_z = 3600 s`, `p_c 0.1`, `τ_syn 5 ms`, axonal delay `3 ms`, `τ_OU 5 ms`,
`w_ei 2 h0`, `w_ie = w_ii = 4 h0`. Calcium thresholds originate in Graupner & Brunel 2012, *PNAS* 109:3991 (`MEMORY`).
All are used **as ratios to h0** so the published proportions survive the move to conductances.
`jlubo/brian_network_plasticity` has **no licence file**: equations and published values are reused,
the code is written fresh. `jlubo/memory-consolidation-stc` is Apache-2.0.

### Neuromodulator-dependent protein synthesis — Lehr, Luboeinski & Tetzlaff 2022, *Sci Rep* 12:17772, doi:10.1038/s41598-022-22430-7 — `READ`

`θ_pro = h0 / (NM + 0.001)`, read from `Network.cpp`. NM levels 0.06 / 0.18 are the paper's low / high.
**Scale correction:** `θ_pro` thresholds a *sum over incoming synapses*, defined for in-degree 160. At
in-degree K it is multiplied by K/160 (`scale_theta_pro_by_indegree`, on), so it equals the published
value at the reference size. Decided on structural grounds before any recall number existed.

### T-type calcium current — Destexhe, Bal, McCormick & Sejnowski 1996, *J Neurophysiol* 76:2049; data of Huguenard & McCormick 1992, *J Neurophysiol* 68:1373 — kinetics `READ` from ModelDB 3343 `IT.mod`; papers themselves `MEMORY`

`m_inf`, `h_inf`, `tau_h`, shift 2 mV, q10 3 from 24 °C: verbatim. **`g_T = 100 nS` is not from that
model** (theirs is a density on a 29,000 µm² cell). It was set by `tests/test_neuron.py`: 100 ms at
−250 pA → a 4-spike rebound burst; 50 ms → 2 spikes; 20 ms → none. `hT_loaded = 0.4` is the gate value
at which that burst appears. `E_Ca = 120 mV` (their Nernst value, rounded).

### Spike mechanism — adaptive exponential integrate-and-fire, Brette & Gerstner 2005, *J Neurophysiol* 94:3637 — `MEMORY`

`C 200 pF`, `gL 10 nS`, `EL −70`, `VT −50`, `ΔT 2 mV`, `a 2 nS`, `b 40 pA`, `τ_w 150 ms`: within the ranges
of that paper's regular-spiking set; not fitted to anything. I cells: no adaptation, no T-current,
`C 100 pF`. **AdEx has no spike waveform** — the upstroke is cut at −40 mV — so gap-junction
*spikelets* are under-represented; the low-pass test therefore uses subthreshold sinusoids.

### Slow GABA_B-like K⁺ conductance — added by this build, no fitted source

`E_K −95 mV`, `τ 150 ms`, `1 nS` per I→E spike. **Why it exists:** with GABA_A alone inhibition
reverses at −80 mV, `h_inf(−78 mV) = 0.32`, and the LOADED state was unreachable (measured **0.0000**
of encode time) — the T-current could never be de-inactivated by the network, and its ablation
would have been a no-op reported as a null. Thalamic rebound bursting rests on GABA_B for the same
reason (`MEMORY`). Values are order-of-magnitude, not fitted.

### Gap junctions — Galarreta & Hestrin 1999, *Nature* 402:72; Gibson, Beierlein & Connors 1999, *Nature* 402:75 — `MEMORY`

Coupling coefficient target 0.10 (range 0.05–0.15), p = 0.3 within ±8 on a ring. Pairwise
`g = CC·gL/(1 − CC)`; `tests/test_gap.py` **measures** CC in an isolated pair. In the network a cell
has several partners, so its effective CC to any one of them is lower. E–E coupling: off, and
flagged weakly supported.

### Auditory periphery — Zilany, Bruce & Carney 2014, *JASA* 135:283, via `cochlea` (Rudnicki et al. 2015, *Cell Tissue Res* 361:159) — package `READ` (run here), papers `MEMORY`

Human parameters, 100 kHz, CFs 125 Hz–8 kHz (the model's human floor is 125 Hz, so the configured
80 Hz is raised and the run says so), 6/2/2 HSR/MSR/LSR fibres per CF, 60 dB SPL per stream.
`cochlea` is **GPL-3.0** and builds only against Cython < 3. Streams are summed acoustically
before the cochlea. `mixing.g_in_mean_nS` normalises input weight so every front end delivers the
same mean conductance.

### Population signals

LFP proxy: Mazzoni et al. 2015, *PLoS Comput Biol* 11:e1004584 — the 6 ms delay and 1.65 weight are
`MEMORY`. TRF: Crosse et al. 2016, *Front Hum Neurosci* 10:604 — `MEMORY`, method reimplemented.
Phase-lag benchmark: Doelling et al. 2019, *PNAS* 116:10113, doi:10.1073/pnas.1816414116 — `READ` in
full: evoked-model PCM 0.245, oscillator-model 0.58, MEG 95 % CI (0.30, 0.57) L / (0.35, 0.59) R over
1–8 notes/s. **Those MEG numbers are from humans listening to piano music; this is a 250-cell
network hearing noise bursts.** Landing inside the CI is a shape match, not a validation of the cells.

### Lehr reproduction — reference stimulus

The learning-stimulus amplitude `(N f + √(N f) ξ)·1 s·h0`, N = 25, f = 100 Hz, is taken **literally**
from the Brian2 reference and was not cross-checked against the C++ implementation.

### Recall-phase drive, candidate 1: NM → excitatory excitability — Bacon, Pickering & Mellor 2020, *Cereb Cortex* 30:6135, doi:10.1093/cercor/bhaa159 (PMC7609922) — source supplied by the operator; held in the library; **introduction `READ`, results and methods not read**

The claim taken from it: endogenous LC noradrenaline raises CA1 pyramidal excitation–spike coupling via
β-adrenoceptors **without changing feedforward excitatory or inhibitory input**. Its introduction names
block of the slow AHP as NA's most robust excitability effect (Madison & Nicoll 1982, `MEMORY`).

| parameter | value | source |
|---|---|---|
| `nm_excitability.ahp_block_per_nm` | 1/0.3 | **placeholder.** Anchor: the AHP-like current (AdEx `w`) is fully blocked at the recall NM level, `nm_ref + pulse_amp` = +0.3. "Full block" follows the sAHP literature qualitatively; the number is ours |
| `nm_excitability.dVT_mV_per_nm` | 2 mV / 0.3 | **placeholder.** A 2 mV threshold drop at the same NM level; not taken from the paper |
| `nm_excitability.strength` | 1 (sweep: 1, 2, 4) | multiplies both; **the sweep was declared before any run and is reported whole** |
| `mechanisms.nm_excitability` | **off** | with it off the equation *text* is byte-identical to the published-results model, verified by reproducing a committed run exactly |
| `mechanisms.nm_inhibitory_setpoint` | on | the base model lets NM bias the I cells; the drive as specified must **not** raise inhibition, so its conditions are run with this off as well as on |
| recall modes `nm_sustained`, `cue_nm` | — | NM elevated by `pulse_amp` for the whole probe. Needed because the 1 s `nm_pulse` sits entirely inside the guarded window the score excludes, so an NM-tied drive would act only where nothing is scored |

E cells only; neutral at the reference NM level (unit-tested). **What it is not:** a model of β-AR signalling,
of the sAHP's kinetics (AdEx `w` has τ = 150 ms; a real sAHP lasts seconds), or of CA1.
**Held for later, deliberately not built:** a disinhibitory drive (**ACh-like, not LC** — PMC8513881) and
theta-to-threshold, which goes last because it can make cells fire regardless of content.

## What is NOT built, stated so nobody has to discover it

- **CoNNear inversion (the PRIMARY playback) has never run.** No TensorFlow, no weights; weights are
  academic/non-commercial. The module raises. **Every playback so far is the vocoder fallback.**
- **cnmodel** brainstem stage: raises (needs NEURON). **MSO stage**: built and unit-tested on synthetic
  spike trains, not wired — the loader averages stereo to mono.
- **Video / retina**: interface only. **Event-camera comparison**: reports `unavailable`.
- Nothing here has been **listened to**. Audio is written, never auditioned (monorepo rule).
- Scale: every result so far is at 200 E / 50 I. The 800 / 200 default in the brief has not been run.
