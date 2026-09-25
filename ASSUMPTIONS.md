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
| `mechanisms.nm_recall_only` | **off** | D1. Multiplies the NM excitability term by a phase gate that is exactly 0 outside recall segments, so salience-triggered NM bursts cannot engage the drive during encoding. The gate is an externally imposed *phase schedule* (like `NM(t)` itself), not a network-internal signal. **Any future drive run uses it on** |
| recall modes `nm_sustained`, `cue_nm` | — | NM elevated by `pulse_amp` for the whole probe. Needed because the 1 s `nm_pulse` sits entirely inside the guarded window the score excludes, so an NM-tied drive would act only where nothing is scored |

E cells only; neutral at the reference NM level (unit-tested). **What it is not:** a model of β-AR signalling,
of the sAHP's kinetics (AdEx `w` has τ = 150 ms; a real sAHP lasts seconds), or of CA1.
**Held for later, deliberately not built:** a disinhibitory drive (**ACh-like, not LC** — PMC8513881) and
theta-to-threshold, which goes last because it can make cells fire regardless of content.

### Binaural front end, MSO, neurophonic, ephaptic term (2026-09-21) — **every number below is a placeholder unless marked**

Sources and how far each was read: **Goldwyn, Mc Laughlin, Verschooten, Joris & Rinzel 2014**, *J Neurosci*
34(35):11705, doi:10.1523/JNEUROSCI.0175-14.2014 — held in the library, **not read this build**; the claim used
(postsynaptic current flow is the dominant generator of the MSO field, spikes contribute negligibly) is the
operator's summary and matches this monorepo's own port of that model (`simulators/mso-neurophonic`).
**Goldwyn & Rinzel 2016**, *J Neurophysiol* 115:2033, doi:10.1152/jn.00780.2015 — **not obtainable open-access,
unread**; "mV-scale field → mV-scale membrane perturbation" is the operator's summary. **Verschooten et al. 2019**,
*Hear Res* 377:109 (PMC6524635) — held, title only. Woodworth's formula and the MNTB inhibition-leads
arrangement (Grothe 2003) — `MEMORY`.

| parameter | value | source / status |
|---|---|---|
| spatialiser ITD | Woodworth, head radius 8.75 cm, c = 343 m/s → 381 µs at 45°, 656 µs at 90° | textbook formula, `MEMORY`; asserted ≤ the monorepo's 660 µs ceiling; applied as a fine-structure delay of the whole waveform |
| spatialiser ILD | `20 dB · sin(az) · f²/(f² + (1.5 kHz)²)` | **placeholder** for the *shape* of a head shadow. **Not an HRTF** — no pinna, elevation or distance cues. HRTF rendering is not built |
| stream azimuths | −45°, +45°, 0°, −90°, +90° by stream index | arbitrary; a stereo *file* is used as recorded, with no spatialiser on top |
| two cochleae | Zilany 2014, independent per ear (spike-generator seeds `seed`, `seed + 5000`); fibre populations `hsr_L … lsr_R` | as the mono front end. Level is set on the L/R *mean* power so the rendered ILD survives calibration |
| `mso.cf_max_hz` | 1500 Hz | Verschooten et al. 2019 (fine-structure phase-locking limit). **Envelope ITD at higher carriers is out of scope** |
| `mso.delays_us` | −600 … +600 in 100 µs steps | a Jeffress-style delay map; whether the mammalian MSO has one is contested, and this does not take a side — it is a readout convenience |
| `mso.tau_e_ms`, `tau_i_ms`, `tau_m_ms` | 0.2, 0.5, 0.3 ms | order-of-magnitude for mature MSO; not fitted |
| `mso.inh_lead_ms`, `w_inh` | 0.3 ms, 0.5 × EPSC | contralateral glycinergic inhibition arriving *before* contralateral excitation; placeholder |
| `mso.theta_epsp`, `t_ref_ms` | 3 EPSPs, 1 ms | **first guess, never adjusted**: with these the best internal delay tracks the imposed ITD to within one 100 µs step (unit-tested) |
| MSO scope | **one** MSO (ipsilateral = left); leaky coincidence units in numpy, not a biophysical cell | `simulators/mso-neurophonic` is the biophysical model and cannot spike (no sodium channel), which is why it is not the stage |
| neurophonic | sum over MSO units of (ipsi EPSC + contra EPSC − IPSC), kept at 5 kHz | computed from **postsynaptic currents, never from spikes** (Goldwyn et al. 2014). Units are EPSC units — a shape, not microvolts |
| `ephaptic.r_field_Mohm` | 1 MΩ | maps mean net synaptic current per cell (≈ 1 nA while encoding) to a **mV-scale** field, by construction. There is no geometry here, so this is a scale choice, not a measurement |
| `ephaptic.g_eph_nS` | 0 (off); sweep 1 and 3 nS, declared before any run | dV_m/V_field = g_eph/g_L = 0.1 and 0.3. **At 0 the term is absent from the equation text**, and a run reproduces exactly (tested) |
| ephaptic form | `I_eph = g_eph · (V_field,network + V_field,neurophonic)` | **fields sum linearly; there is no field × field term** (asserted against the equation text). All nonlinearity is the membrane's. Sign: net inward synaptic current → depolarising |
| distortion products | measured in the AN PSTH and in the network's population signal; **never added** | see `RESULTS.md` for what the Zilany model does and does not produce |

### Retrieval-as-writing and iterative settling (2026-09-21) — all switches default OFF; every number is a placeholder

**Hard rule, enforced by construction:** nothing outside the neurons holds the trace or does completion. Every
gating or re-injection signal is computed from network-internal quantities (synaptic currents, calcium, the
cells' own spikes). Stream labels, stored-assembly identity and decoder output are analysis-only and never feed
back. The one exception is labelled as such: `eval.freeze_plasticity_at_recall` (C6) is an **evaluation mode,
not biology**. With every switch off the equation text is hash-pinned to the published-results model.
**Status: implemented and unit-tested; NO experiment has been run** — the operator's precondition (a drive
condition beating the foreign-stream null) was not met.

| component | parameter | value | status |
|---|---|---|---|
| **C1** `mechanisms.intrinsic_trace` | — | off | The trace **is the existing CREB-like variable** (no parallel state): raised by encoding activity via somatic calcium, acts bounded to [0, 1], slow decay (`creb.tau_s`). Needs `mechanisms.creb`. **It gates reactivation and allocation and cannot store content** — it is one scalar per cell, so its capacity is bounded by the cell count regardless of what was stored; content stays in the synapses. Operator-supplied sources for that limit, **unread**: *Nat Commun* 2025, s41467-025-66975-3; *J Neurosci* 2024, e0846232024 |
| C1 | `intrinsic_trace.k_ahp` | 0.5 | placeholder: fraction of the AHP-like current removed at trace = 1 |
| C1 | `intrinsic_trace.dVT_mV` | 2 mV | placeholder: extra threshold lowering at trace = 1, on top of `creb.dVT_mV` |
| **C4** `mechanisms.prior_drift` | `prior_drift.erosion_per_spike` | 0.01 | placeholder. The trace loses this fraction **per spike of its own cell** — erosion per *use*, independent of any synaptic rate, so the prior can drift while the synaptic trace does not |
| **C4 option** `mechanisms.prior_repulsion` | `repulsion_mV`, `tau_use_s`, `use_per_spike` | 2 mV, 5 s, 0.1 | placeholder. A fast recent-use variable **raises** threshold ("seek novel"). **Sign unsettled**: the adaptation literature reports both attractive and repulsive tuning shifts (`MEMORY`, no source read); only the repulsive form is implemented, and it is its own switch |
| **C2** `mechanisms.mismatch_gate` | `tau_ms`, `eps_pA` | 50 ms, 1 pA | placeholder. Per cell, mismatch = \|I_ff − I_rec\| / (\|I_ff\| + \|I_rec\| + eps) on the cell's **own** low-passed feedforward and recurrent excitatory currents; pooled to one population value (the mean over E cells). A silent cell reads 0. Note both *input-only* and *recurrent-only* states read as high mismatch — it is an unsigned contrast |
| C2 | `theta_low`, `theta_high` | 0.2, 0.6 | **placeholder. Declared sweep, fixed before any run: (0.1, 0.5), (0.2, 0.6), (0.3, 0.8); the whole sweep is to be reported.** Below low: retrieval only, the write is off. Between: lability window for the active assembly (C3). Above high: new-trace mode |
| C2 | `z_protect`, `creb_ref` | 0.1, 0.2 | placeholder. In new-trace mode the write is scaled by the postsynaptic cell's allocation bias `clip(creb/creb_ref, 0, 1)` (C1's variable) and **blocked where z ≥ z_protect** — the consolidated assembly is protected. The gate acts on early-phase induction and its noise; capture of already-tagged synapses is not gated |
| C2 | sources | — | prediction-error boundary conditions for reconsolidation: PMC7820768; **and the failed replication: PMC8831535**. Operator-supplied; **read depth: abstracts, not read by this build** |
| **C3** `mechanisms.lability_window` | `lability.gain`, `lability.tau_s` | 3×, 5 s | **placeholders, including the duration.** A cell is *reactivated* when it spikes while its **own** recurrent excitatory current exceeds its feedforward one; that opens a plasticity gain on synapses onto it, which decays back to baseline (restabilisation). Alone: a gain on top of ordinary plasticity. With C2: in the mid regime **only** reactivated cells are written. `tau_s` is simulated seconds and is not time-compressed |
| **C5** `sim.log_provenance` | — | off | **analysis only; the network never sees it.** At each E spike the cell's own `g_ext`, `g_e` and `V` are recorded and the feedforward and recurrent excitatory currents formed in analysis. A spike is *recurrently reconstructed* when I_rec > I_ff, *cue-driven* otherwise. It adds nothing to the equations, and a test asserts the spike train is identical with it on and off. The 50/50 boundary is a convention, not a measurement |
| **C6** `eval.freeze_plasticity_at_recall` | — | off | **NON-BIOLOGICAL evaluation mode.** Induction, its noise and late-phase capture are switched off during recall segments by an externally imposed schedule — the one signal in this work that does not come from inside the network, which is why it lives under `eval`, not `mechanisms`. It is the ground truth a lossy (plastic) read is compared against. Passive early-phase decay continues (tested: during a frozen recall the weights move by passive decay only) |
| **C8** `mechanisms.iterative_settling` | `settling.k_cycles` | 1 (declared set: 1, 2, 4, 8) | Recall as K cycles, the cue re-presented each cycle. **K = 1 builds the base network exactly — no projection exists — and a test asserts the spike train is bit-identical.** Consequence, stated: K = 1 and K > 1 differ both in re-presentation *and* in the presence of the projection during encoding |
| C8 | **route: (a) a delayed feedback projection with learned weights** | — | **Chosen over (b) theta-gated reopening of the input window.** Reason: (b) carries nothing from one cycle to the next except ordinary persistence, and this network has none — recall-phase firing falls to ~0.01 Hz within the gap (RESULTS.md). (a) is an explicit route whose content is *learned*. It uses the **same calcium/STC rule** with the ordinary 18.8 ms calcium delay, so learning is auto-associative, while its output arrives **one cycle late**. It delivers only its learned part, `g0_fb · clip(h − 1 + z, 0, 10)`, so an untrained projection carries exactly nothing — fixed random feedback would not count, and cannot occur. **Decoder output is never re-injected.** |
| C8 | `settling.cycle_gap_s`, `p_fb`, `g0_fb_nS` | 1 s, 0.1, 1 nS | placeholders. Cycle period = cue + gap (2.5 s at `quick.yaml`). **A 2.5 s conduction delay is not a synapse**: it stands for a multi-synaptic re-entrant loop and is not modelled as one |
| **C8b** `settling.multi_view` | — | off | each cycle presents a **different** subset of cue channels of the same size (rotating through a fixed permutation), to test completion from rotating views against a fixed view |
| **C7** `protocol.cue_channel_fraction` | 1.0 (declared set: 0.25, 0.5, 0.75, 1.0) | — | fraction of **input channels** the cue drives; at 1.0 with one cycle the filter is skipped, so the base path is untouched |
| C7 | completion metric | — | decode from cells the cue did **not** drive. **Known limit, found while building:** each E cell receives ~10 % of the input channels (~32 of 320), so the strict set (no cue input at all) is empty at every declared fraction — P(no cue input) ≈ 0.9⁸⁰ at 25 %. The experiment reports the strict count and falls back to the **least-driven quartile, labelled as weaker** (those cells *are* cue-driven, just least) |
| C7 | `exp completion` | **never run** | 31 declared conditions. Blocked in code by the operator's precondition (a drive condition must first beat the foreign-stream null; `recall_drive` gave 0 of 18) |

### P1 — the plasticity rule calibrated in isolation (2026-09-21) — `plasticity/calibrate.py`, `tests/test_plasticity_protocols.py`

**Why.** The storage diagnostic found 0 of 1398 tags were potentiation: calcium crosses θ_d routinely and θ_p almost
never. The thresholds had never been checked against standard induction protocols. Harness: one pre and one post
cell driving the model's actual synapse equations, no network, no noise, time compression 1. Expected outcomes were
written into the test file before the first run.

| parameter set | a TBS → pot | b HFS → pot | b capture | c +10 ms → pot | d −10 ms → dep | e LFS → dep | score |
|---|---|---|---|---|---|---|---|
| **current** — Luboeinski & Tetzlaff 2021 (`READ`) | **−0.203 dep** ✗ | +0.888 ✓ | ✓ | **0.000** ✗ | **0.000** ✗ | **0.000** ✗ | 2/6 |
| Graupner & Brunel 2012, hippocampal slices | +0.854 ✓ | +0.939 ✓ | ✓ | **−0.258 dep** ✗ | −0.173 ✓ | −0.316 ✓ | 5/6 |
| Graupner & Brunel 2012, cortical slices | +0.457 ✓ | +0.594 ✓ | ✓ | +0.181 ✓ | −0.433 ✓ | **0.000** ✗ | 5/6 |
| **adopted** — G&B hippocampal with **θ_p 1.30 → 1.18** | +0.885 ✓ | +0.944 ✓ | ✓ | +0.206 ✓ | −0.173 ✓ | −0.316 ✓ | **6/6** |

(values are Δh in units of h₀, read 10 s after the protocol)

- **The current set fails four of five.** A single pre–post pair peaks at Ca ≈ 0.77, below θ_d = 1.2, so 1 Hz pairing
  and LFS do nothing at all; a theta burst peaks near 1.8–2.3 — above θ_d, below θ_p = 3.0 — and **depresses**.
  Only sustained 100 Hz reaches θ_p. This is the mechanism behind the diagnostic's depression-only write.
- **No published set passes all five**, so the brief's last resort was used: one parameter, **θ_p only**, stepped down
  from its published 1.30 in 0.01 steps on the hippocampal set, stopping at the **first** value where all five pass:
  **1.18** (the eleven values from 1.29 to 1.19 fail on protocol c). θ_d and every other value are as published.
  The scan is in `docs/results/p1_theta_p_scan.json`. The outcome moves in *steps* (at 1.23, 1.20, 1.18) because the
  plasticity ODEs run on a 1 ms clock and the time calcium spends above θ_p in protocol c is ~1–2.5 ms: **the
  calibration is sensitive to that clock**, and the window that satisfies both c and d is narrow (1.153 < θ_p ≲ 1.19).
- **Adopted as a preset, not as the default:** `plasticity.preset: gb2012_hippocampal_cal`. The default stays
  `luboeinski2021` so every committed run still reproduces bit-for-bit; a pinned test records that the default passes
  only HFS. Values: `Ca_pre 1.0`, `Ca_post 0.275865`, `θ_p 1.18` (published 1.3), `θ_d 1.0`, `τ_Ca 48.8373 ms`,
  `t_Ca_delay 18.8008 ms`, `γ_p 1645.59`, `γ_d 313.0965`, `τ_h 688.355 s`. `σ_pl`, `h_max`, `θ_tag`, `θ_pro`, `τ_p`, `τ_z`
  and the h-form of the rule are unchanged (Luboeinski & Tetzlaff).
- **⚠ Read depth of the Graupner & Brunel values: `MEMORY`.** *PNAS* 109:3991, doi:10.1073/pnas.1109359109 has **no
  open-access copy the library could retrieve**, so both G&B parameter sets above were entered from memory of its SI
  table and **have not been read this build**. One check is available and passes: five of the hippocampal values
  (48.8, 18.8, 1645.6, 313.1, 688.4) equal the Luboeinski config to its printed precision, and Ca_post/Ca_pre = 0.2759
  matches 0.1655/0.6 — the current set is that set with calcium amplitudes × 0.6 and the thresholds moved
  (θ_d 1 → 1.2, θ_p 1.3 → 3.0). `Ca_pre = 1`, `θ_d = 1`, `θ_p = 1.3` and the whole cortical set are **uncorroborated**;
  verify against the paper before relying on them.
- **A consequence to expect in the network:** with `Ca_pre = 1.0 ≥ θ_d = 1.0`, **every presynaptic spike on its own
  reaches the depression threshold.** That is how the slice-fitted set produces LFS-LTD, and in a spontaneously active
  network it means background firing depresses. The Luboeinski scaling (× 0.6, θ_d 1.2) is what removed that in vivo.
- Decisions the brief left open, fixed before the first run: pot / dep = Δh ≥ +0.1 / ≤ −0.1 h₀; in a and b the post
  cell fires 5 ms after each pulse (pre-only is reported, not scored); LFS is pre-only; capture = z > 0.05 ~16 min
  after HFS with the protein pool held at 1, and z = 0 with it empty.

### P2 — plastic input→E synapses — `mechanisms.input_plastic` (default off)

Same rule as E→E (`stc.plastic_model`, `ON_POST`, the same namespace), acting on `g_ext` with the NM input gain kept;
its early-phase change feeds the postsynaptic cell's protein trigger through `sum_h_diff_in`, and the in-degree scale of
θ_pro then counts both projections ((20 + 32)/160). Input→I synapses stay fixed. The weight snapshots cover input→E
when the switch is on. Off = the published text and a bit-identical run (tested).

## Minimal habituation model (2026-09-23) — `neurotape.habituation`, `configs/habituation.yaml`

This is a separate model. It shares only the auditory-nerve package, the experiment plumbing and the provenance stamp with
the full model. The preregistration, including exactly what was seen before it was written, is `docs/habituation/PREREG.md`.

**Read depth for this section.**

- Tsodyks & Markram 1997 (*PNAS* 94:719): the model excerpt was `READ` through scite ("recovers with a time constant of about 1 sec").
- Ulanovsky, Las, Farkas & Nelken 2004 (*J Neurosci* 24:10440): abstract `READ` ("several time scales concurrently … from
  hundreds of milliseconds to tens of seconds"), plus one citing passage placing corticocortical depression recovery in the
  same range.
- Rankin et al. 2009 (*Neurobiol Learn Mem* 92:135): abstract only. **The numbered characteristics used as checks are `MEMORY`.**
- Groves & Thompson 1970 (dual-process theory): `MEMORY`.

| parameter | value | source / how set |
|---|---|---|
| relay stage | pooled AN rate per CF − its own spontaneous rate, rectified, × 150/250 Hz, + 1 Hz spontaneous | **placeholder** for a low-spontaneous thalamic (MGB-like) input. It exists because HSR auditory-nerve fibres fire ~43 spikes/s pooled in silence (measured here), and a depressing synapse driven by that is depleted by silence. MGB is not a subtraction |
| relay units | 32 CF × 8, independent Poisson | placeholder |
| `depression.U`, `tau_fast_s` | 0.5, 0.8 s | one-pool depression, recovery ~1 s (Tsodyks & Markram 1997, `READ`); U placeholder |
| `a_slow`, `tau_slow_s` | 0.05 per unit release, 20 s | "tens of seconds" (Ulanovsky 2004, abstract `READ`); `a_slow` placeholder. Depletion is per unit **release**, not per spike, so a fast-depressed synapse also spares its slow pool |
| tonotopy | Gaussian in log-frequency, σ 0.3 oct, cut at 5 %, 80 % connection probability, ×U(0.7, 1.3) | placeholder |
| LIF cells | C 200/100 pF, gL 10 nS, EL −70, VT −50, Vr −60 mV, 2 ms refractory, τe 5 ms, τi 10 ms, 3 mV membrane noise | textbook values, not fitted |
| `I0_pA`, `w_in_nS` | 80 pA, 8 nS | **operating-point scan** (below), against C1/C2 only |
| E→I, I→E | p 0.2 × 2 nS, p 0.3 × 4 nS | placeholder |
| `longterm.pre_spont_L` → `eta_pre` | 0.8 | **derived**: the rate at which spontaneous release alone holds L at 0.8. An absolute rate would mean nothing |
| `longterm.eta_hebb` | 0.05 | engagement criterion C3: stored-channel L after 16 presentations = 0.871 (rate periphery) / 0.876 (AN). Scanned 0.002, 0.005, 0.02, 0.05 → 0.994, 0.984, 0.942, 0.871 |
| `longterm.tau_s` | 3600 s | placeholder; a ×6 / ÷6 sweep is declared in PREREG, not run |
| `salience.theta` | 0.5 × the naive neutral onset drive | placeholder |
| NM gain | **solved** per run and mode: loud (+15 dB) calibration sounds peak at NM = 1.0 | C5 — without it `network` NM started ~30× below `raw` |
| `salience.gain`, `eta_pot` | 1.0, 0.10 | gain placeholder; `eta_pot` = 2 × `eta_hebb` (definition C6) |

**Operating-point scan** (rate periphery, seed 0; C1 spontaneous 0.2–2 Hz, C2 response ≥ 3× spontaneous and ≥ 30 % of cells):

| I0 | w_in 2 | 4 | 8 | 12 | 16 |
|---|---|---|---|---|---|
| 80 pA | | | 0.29 Hz / 4.7× ✓ | 0.76 Hz / 2.8× | 1.24 Hz / 2.1× |
| 90 pA | 0.09 Hz / 2.9× | 0.17 Hz / 3.9× | 0.52 Hz / 3.2× | 1.0 Hz / 2.2× | 1.5 Hz / 1.8× |
| 110 pA | 0.56 Hz / 1.5× | 0.75 Hz / 1.7× | 1.11 Hz / 1.7× | | |
| 130 pA | 1.10 Hz / 1.2× | 1.20 Hz / 1.3× | 1.46 Hz / 1.3× | | |

The first setting tried (150 pA, 1.2 nS) gave a response indistinguishable from spontaneous firing: there was nothing to habituate.

**Two defects found by the model's own tests, both fixed before any recognition readout.**

1. NM was left non-zero by the settling period before calibration, so the solved gain gave 0.97 rather than 1.00.
   Salience is now inert until calibrated.
2. The Hebbian fast-forward used the mean postsynaptic trace, and under-estimated erosion in silence by ~30 %.
   A relay spike makes its own target fire, so release and the trace are correlated. The factor is now measured by 10 s
   of direct simulation per run, and the fast-forward is tested against direct simulation.

**What it is NOT:** it has no E→E recurrence, no adaptation current, no T-current, no consolidation machinery, no
hippocampus and no second modality. Each probe goes to its own copy of the network, which is the numerical equivalent of
separate animals and is not a biological operation.

### E02 mechanisms (model-v0.2.0, 2026-09-24) — default OFF; values used by E02 are in its config.yaml

- **Feedforward inhibition** (`ffinh`): 50 tonotopic LIF FF cells (I-cell membrane), relay→FF 0.6 nS with no
  short-term depression, FF→E 0.3 nS × G, g0 = 1. Operating point chosen by a scan on off-list seeds against a
  target stated before the scan (FF 20–60 Hz driven, naive E response cut 20–35 %): `[ARBITRARY]`. FF cells are
  silent at rest at this operating point.
- **iSTDP** — Vogels et al. 2011, *Science*, doi:10.1126/science.1211095 —
  abstract `READ` (full text closed); the rule's equation from `MEMORY`. η = 0.015 by an engagement criterion on
  the synaptic variable (top-decile G ≈ 2 g0 after 20 presentations): `[ARBITRARY]`. τ_s = 1 h, matched to the
  Hebbian L.
- **Receptor inactivation** — Rajan & Marshall 2025, *Curr Biol*, doi:10.1016/j.cub.2025.05.071 — `READ` (Methods).
  k_rec 0.1, k_deg 0.02, k_des 0.005 **read per minute** (the paper gives no unit; stimuli were one per minute).
  Their eq. 2 prints −(k_rec − k_deg + k_des); +k_deg used, as the text says both pools degrade. k_int = 2e-4 per
  unit release `[ARBITRARY]`. Per relay fibre, not per synapse (every synapse of a fibre sees the same release).
  **Their model drains untrained surface receptors under a synthesis block**; Stentor's untrained baseline survives
  in their account through a hard output threshold, which this network does not have.

### Single-cell Stentor models (model-v0.3.0, 2026-09-25) — `neurotape.singlecell`

- **Receptor inactivation** — Rajan & Marshall 2025, doi:10.1016/j.cub.2025.05.071 — Methods `READ`, authors' MATLAB v9
  `READ` (reimplemented, not copied; the repo has no licence). Parameters as published: k_int 0.1, k_recycle 0.1,
  k_synth 0.7, k_deg 0.02, k_des 0.005 (per minute), F_mid 1.5, scale 0.6, S_a 1000, S_b 0.00025, V_th 0.012.
  `V_i = 1` and `io_max = 1` are the code's stated conventions, not printed in the paper. S* = 35 receptors; a
  contraction needs more than n_min = 12 open. Forces used in tests (1.0 low, 4.0 high) are `[ARBITRARY]`: the
  figures' force values are not in the paper or the code.
- **Gating variant** — Wood 1988 (J Neurosci 8:2248), cited through Rajan et al. 2022 [FT]; Wood itself not read.
  Modified receptors revert at k_rec and turn over at basal k_deg; none destroyed. The reversion rate is taken from
  the published model's recycling rate `[ARBITRARY: no measured gating-reversal rate]`.
- **Two channels** — independent pools with identical parameters, converging on one membrane `[ARBITRARY]`; motivated
  by Stentor's modality specificity (mechanical does not transfer to light or electrical; Wood, cited in Rajan &
  Marshall 2025 [FT]).
- **Labile recycling factor** (model-v0.4.0, off by default) — Rajan et al. 2026, doi:10.1016/j.cub.2026.03.080 [FT]:
  a translation block accelerates habituation and prolongs retention while untrained responses hold; the authors
  propose that recovery requires new protein synthesis and that an unstable protein may set the learning rate. The
  factor's form (first-order turnover, multiplying recycling) and its rate k_x = 1/60 min⁻¹ are `[ARBITRARY]`.
- **Slower basal turnover** (`k_deg_scale`, model-v0.4.0) — `[ARBITRARY]`; k_syn scales with it so S* stays 35.

## What is NOT built, stated so nobody has to discover it

- **CoNNear inversion (the PRIMARY playback) has never run.** No TensorFlow, no weights; weights are
  academic/non-commercial. The module raises. **Every playback so far is the vocoder fallback.**
- **cnmodel** brainstem stage: raises (needs NEURON). The **MSO stage is wired** (2026-09-21): one side only,
  fine-structure ITD only; no LSO, no ILD computation, no envelope ITD, no HRTF — `docs/DEFERRED.md`.
- **Video / retina**: interface only. **Event-camera comparison**: reports `unavailable`.
- Nothing here has been **listened to**. Audio is written, never auditioned (monorepo rule).
- Scale: every result so far is at 200 E / 50 I. The 800 / 200 default in the brief has not been run.
