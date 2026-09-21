# neurotape — results of the first full run (2026-09-21)

**Configuration:** `configs/quick.yaml` — 200 E / 50 I, auditory-nerve front end, 10 s of encoding,
recall probed at 5 s / 30 s / 120 s of simulated delay (= 5 min / 30 min / 2 h of slow-process time
at **60× time compression**). **10 seeds per condition, a different synthetic stimulus per seed,
0 failed runs out of 340.** Every per-seed number is in `<experiment>/runs.json`.

> **The headline: it does not work as a tape, and nothing in it helps.** Encoded activity can be read
> (held-out r 0.5–0.8). Recall cannot: decoded recall activity correlates with the stored stream at
> r ≈ 0 at every delay, in every condition. No mechanism beats its ablation. The plain reservoir is
> *better* at encoding. Opus and AAC win by ~1.0 in r. This is a statement about a **model at one
> small scale with synthetic streams**, and the predicted outcome — tagging-and-capture networks
> store *which cells*, not *when*.

| # | question | result (mean [95 % CI], n = 10) | verdict |
|---|---|---|---|
| 1 | reconstruction vs delay, one stream | encode 0.832 [0.787, 0.878]; recall −0.029 / −0.003 / +0.038 at 5 min / 30 min / 2 h, all CIs span 0 | **no recall**; spiking − ESN = +0.04 [−0.07, +0.16] → does not beat the reservoir |
| 2 | 2 and 3 simultaneous streams | encode r per stream 0.81 / 0.28 (2 streams), 0.48 / 0.13 / 0.75 (3); recall all ≈ 0; recall crosstalk ≈ 0 everywhere | streams are **unequally** encoded; nothing is recalled |
| 2 | stream identity from **rank** | 77.4 % [75.7, 79.0] vs permutation-null 95th pct 56.8 %; p < 0.05 in **10/10** seeds. From the binary fired vector: 65.8 %, 9/10 | **YES — and rank beats win/lose.** The one clearly positive finding |
| 3 | single-mechanism ablations | recall: every (full − ablated) CI spans 0, **including frozen weights**. Encode: same, except the front end | **no mechanism does detectable work** for recall. Auditory nerve vs filterbank front end: **+0.105 [+0.066, +0.143]** at encoding |
| 4 | baselines | encode: spiking 0.535, **ESN 0.730**, raw-input bound 0.748, shuffled-input floor −0.030 | spiking − ESN at encode = **−0.195 [−0.222, −0.168]**: the reservoir **wins**. Recall: neither recalls |
| 5 | Lehr et al. 2022 NM sweep | NM = 0 → z = 0; core-internal z 0.75 → 0.94 and outgoing z 0.30 → 0.94 as NM 0.03 → 0.18; ρ(outgoing z, NM) = +0.94 | **4/4 pre-registered criteria pass** — *qualitatively*. See caveats |
| P | LFP proxy phase lag vs rate (Doelling 2019) | latency **4 ms**, PCM 0.997, identical for theta free and phase-reset | the test is **uninformative** at this latency, and the model does **not** reproduce ~100 ms cortical tracking. Theta manipulation left no trace; recall ordering ρ ≈ −0.06 / −0.10 (no order) |
| A | attend stream 0 via NM gain | theta-locking shift toward the attended stream +0.013 [+0.003, +0.024]; smear reduction −47 ms [−232, +138] | locking shift is **detected but negligible** (0.013 on a base of 0.38); smear: not detected |
| C | stored size / quality vs codecs | synaptic state 3.2 kbps, with readout 13.4 kbps. Opus 0.905 @ 6.9 kbps, AAC 0.987 @ 11.6 kbps; network recall **−0.107 [−0.191, −0.023]** | the network **loses by ~1.0** even where the codec's floor gave it *more* bits than the network. Video: unavailable |
| S | salience-gated retention of a rare event | event-window recall: gated −0.035, flat-NM +0.045, Opus at the same budget **0.774** | gating: **no detectable benefit**; vs uniform compression: **loses** by 0.81 [0.67, 0.94] |

## Follow-up (2026-09-21): the other two recall modes — `recall_modes/REPORT.md`

Same configuration, one stream, 10 seeds per mode, **30 runs, 0 failed, bit-reproducible** (hash seed pinned — see below).

| mode | recall-phase E rate | time-locked r (guarded) | best-lag r: own stream − 20 foreign streams | seeds with foreign-null p < 0.05 | rate-pattern r vs encoding |
|---|---|---|---|---|---|
| `cue` (first 15 % of the stream) | 0.009–0.011 Hz (~13 spikes) | −0.024 / +0.001 / −0.029, CIs span 0 | +0.033 / +0.011 / +0.028, all CIs span 0 | 1, 0, 1 of 10 | +0.06 / +0.04 / −0.01 |
| `no_cue` (spontaneous replay under noise) | 0.007–0.010 Hz | −0.018 / −0.036 / +0.004 | −0.020 / −0.018 / **−0.027 [−0.047, −0.008]** | 0, 1, 0 of 10 | +0.06 / +0.02 / 0.00 |
| `nm_pulse` (NM pulse, no input) | **0.006–0.009 Hz** | −0.018 / −0.029 / −0.011 | −0.020 / −0.004 / −0.012 | 0, 1, 0 of 10 | +0.06 / +0.02 / 0.00 |

(three values = delays of 5 min / 30 min / 2 h of slow-process time)

- **No mode recalls.** Decoded recall is no closer to its own stream than to 20 other streams from the
  same generator, in any mode at any delay. Expected false positives at p < 0.05: 0.5 per cell of 10.
- **The NM pulse does not wake the network — it quiets it.** Recall-phase firing is *lowest* under the
  pulse. NM raises input gain (there is no input to gain) and the inhibitory set point (which there is).
- **The binding constraint is silence, not a bad readout.** ~13 spikes across 200 cells in 8.5 s: there is
  nothing to decode. With 3.8 % of E→E synapses consolidated at a baseline weight of 1 nS over ~20
  inputs, the network has **no self-sustaining activity** to replay through. The rate-pattern score
  (do the encoding-active cells fire at recall?) is ≈ 0 for the same reason — *nothing* fired, which is
  different from the wrong cells firing. Its settle-period baseline is defined in only 2–3 seeds of 10.
- **The circular-shift null is anti-conservative for near-silent predictions** — it called 6/10 seeds
  significant in one cue cell where the foreign-stream null called 1/10. The foreign-stream null is the
  one to read; the shift null stays in the report, labelled.
- **What this points at:** recall needs a recall-phase *drive* (a disinhibitory or excitatory NM action,
  or theta strong enough to bring assembly cells to threshold) before any storage question can be
  asked. That is a modelling change with its own ablation, not a parameter to nudge.

### Reproducibility note that applies to the first full run

Found while cross-checking this experiment against experiment 1: the same (config, seed) produced one
of exactly **two** spike trains, selected by `PYTHONHASHSEED` — Brian2's code generation orders
expression terms by hash and `-ffast-math` rounds the orderings differently. Both are valid noise
realisations, so the **340-run statistics above are unbiased but not bit-reproducible per seed**. The
hash seed is pinned now (workers inherit it; the CLI re-execs once), and every RNG-consuming object
and synaptic pathway has an explicit scheduling order; two independent CLI invocations now return
identical numbers.

## Recall-phase drive, candidate 1 (2026-09-21) — NM raises excitatory excitability — `recall_drive/REPORT.md`

Mechanism and basis in `ASSUMPTIONS.md` (Bacon, Pickering & Mellor 2020): NM-dependent block of the AHP-like
current plus a threshold drop, E cells only, neutral at the reference NM level, off by default (a committed run
reproduces bit-for-bit with it off). `quick.yaml`, one stream, pinned hash seed, **18 conditions × 10 seeds =
180 runs; 1 failed** (`nm_sustained | drive off`, seed 1: a recall window with *zero* spikes crashed the
best-lag statistic — now a reported outcome with a test; that condition has n = 9).

**Success criterion, fixed before any run:** decoded recall matches its own stream better than 20 foreign
streams — the whole 95 % CI of (own − foreign best-lag r) above zero. Higher firing alone does not count.

### Verdict: 0 of 18 conditions pass. 0 of 54 condition × delay cells pass.

**Multiple-comparison count, kept in view:** 54 cells, each a one-sided 2.5 % test, so **~1.35 passes were
expected by chance and none occurred.** On the other tail, **3 of 54** cells have a CI entirely *below* zero
(`no_cue | off` @ 2 h, `nm_pulse | ×1` @ 30 min, `nm_sustained | ×1, NM-inh off` @ 2 h) against the same
~1.35 expected: nothing to explain on either side. Seeds with foreign-null p < 0.05: never more than 2 of 10 in a cell.

Cells are the three delays (5 min / 30 min / 2 h of slow-process time). `NM-inh off` = NM no longer biases the I cells.

| condition | recall E rate, Hz | own − foreign best-lag r (mean) | passes | reactivation (pattern r) | encode r |
|---|---|---|---|---|---|
| cue · drive off | 0.008 / 0.011 / 0.010 | +0.033 / +0.011 / +0.028 | 0/3 | +0.06 / +0.04 / −0.01 | 0.833 |
| cue · drive ×1 | 0.009 / 0.011 / 0.010 | +0.031 / −0.001 / −0.003 | 0/3 | +0.08 / +0.04 / −0.01 | 0.662 |
| no_cue · drive off | 0.007 / 0.010 / 0.009 | −0.020 / −0.018 / −0.027 | 0/3 | +0.06 / +0.02 / 0.00 | 0.833 |
| no_cue · drive ×1 | 0.007 / 0.010 / 0.009 | −0.010 / −0.029 / +0.006 | 0/3 | +0.08 / +0.02 / 0.00 | 0.662 |
| nm_pulse (1 s) · drive off | 0.006 / 0.009 / 0.008 | −0.020 / −0.004 / −0.012 | 0/3 | +0.06 / +0.02 / 0.00 | 0.833 |
| nm_pulse (1 s) · drive ×1 | 0.014 / 0.017 / 0.016 | −0.008 / −0.022 / +0.004 | 0/3 | +0.08 / +0.02 / −0.01 | 0.662 |
| nm_sustained · drive off (n = 9) | **0.001** / 0.001 / 0.001 | −0.030 / +0.029 / +0.009 | 0/3 | +0.10 / +0.06 / +0.08 | 0.833 |
| nm_sustained · drive off, NM-inh off | 0.007 / 0.010 / 0.009 | −0.011 / −0.023 / +0.015 | 0/3 | +0.06 / +0.02 / 0.00 | 0.826 |
| nm_sustained · drive ×1 | 0.052 / 0.056 / 0.053 | +0.002 / −0.011 / +0.017 | 0/3 | +0.39 / +0.27 / +0.34 | 0.662 |
| nm_sustained · drive ×1, NM-inh off | 0.54 / 0.60 / 0.58 | −0.006 / −0.005 / −0.024 | 0/3 | +0.16 / +0.05 / +0.07 | 0.708 |
| nm_sustained · drive ×2, NM-inh off | 1.77 / 1.79 / 1.79 | 0.000 / −0.028 / +0.002 | 0/3 | +0.32 / +0.15 / +0.19 | 0.561 |
| nm_sustained · drive ×4, NM-inh off | 15.6 / 15.8 / 23.2 | +0.024 / 0.000 / +0.021 | 0/3 | +0.59 / +0.48 / +0.50 | 0.500 |
| cue_nm · drive off | 0.007 / 0.006 / 0.005 | −0.025 / +0.022 / +0.015 | 0/3 | +0.14 / +0.09 / −0.01 | 0.833 |
| cue_nm · drive off, NM-inh off | 0.014 / 0.016 / 0.014 | +0.031 / −0.004 / +0.017 | 0/3 | +0.09 / +0.04 / −0.01 | 0.826 |
| cue_nm · drive ×1 | 0.064 / 0.067 / 0.063 | **+0.057 [−0.003, +0.117]** / −0.015 / 0.000 | 0/3 | +0.44 / +0.34 / +0.39 | 0.662 |
| cue_nm · drive ×1, NM-inh off | 0.56 / 0.58 / 0.59 | −0.015 / −0.006 / −0.003 | 0/3 | +0.22 / +0.08 / +0.10 | 0.708 |
| cue_nm · drive ×2, NM-inh off | 1.79 / 1.79 / 1.84 | +0.004 / −0.031 / −0.015 | 0/3 | +0.40 / +0.19 / +0.20 | 0.561 |
| cue_nm · drive ×4, NM-inh off | 21.1 / 21.3 / 29.1 | +0.054 / −0.002 / +0.072 | 0/3 | +0.60 / +0.56 / +0.53 | 0.500 |

The whole sweep (×1, ×2, ×4) is above; ×1 was fixed from one stated anchor before any run, and no strength was
chosen after looking. The nearest miss is `cue_nm · ×1` at 5 min, lower CI bound −0.003.

### What the drive did and did not do

- **It is a drive.** Recall-phase firing goes from 0.008 Hz to 0.05 Hz (×1), 0.55 Hz (×1 with the NM→inhibition
  coupling off), 1.8 Hz (×2) and 16–29 Hz (×4). Silence is no longer the constraint at ×1 and above.
  Consolidation-phase firing stays quiet (0.008–0.036 Hz), as intended: the drive is tied to elevated NM.
- **Elevated NM without the drive makes things *quieter*** — 0.001 Hz under `nm_sustained · drive off` — because
  the base model's NM raises the inhibitory set point. That confirms the earlier `nm_pulse` finding and is why
  the drive conditions were also run with that coupling off.
- **The reactivation score rises — and it is not memory.** Encoding-active cells fire again under the drive
  (pattern r up to +0.6). A control was run because this number moved: the same drive with **frozen weights**
  (`recall_drive_frozen_control_runs.json`, 40 runs, 0 failed). Reactivation is **unchanged without
  plasticity**: plastic − frozen = 0.000 [−0.006, +0.005] / +0.002 / −0.004 at ×1 and −0.05 [−0.12, +0.02] at ×4.
  So it reflects fixed wiring and excitability — the cells the input drives hardest are the cells a global
  excitability boost recruits first — not a consolidated trace.
  In that control, plastic − frozen on the success statistic has 1 of 6 cells with a CI above zero
  (×4 @ 5 min, +0.068 [+0.011, +0.124]; ~0.15 expected by chance). Neither arm passes the criterion itself, so
  this is noted, not claimed.
- **The drive costs encoding accuracy:** encode r 0.833 → 0.66 (×1) → 0.50 (×4), because salience-triggered
  phasic NM engages it *during encoding* too. A drive confined to the recall phase would need its own gate.
  **Attribution and fix (2026-09-21, D1):** the encoding drop is attributed to NM bursts during encoding, and
  `mechanisms.nm_recall_only` now forces the NM excitability term to exactly zero outside recall segments
  (tested: identically zero through settle and encoding; off = text unchanged). **Any future drive run uses
  `nm_recall_only = on`.** The attribution is an inference from the mechanism, not yet a measurement — no drive
  run has been repeated with the gate on.
- **Read with the first run:** the network now fires at recall and still returns nothing stream-specific, with
  weights frozen or plastic alike. That moves the diagnosis from *"nothing fires"* to *"what fires carries no
  temporal content"* — the expected property of a rate-assembly store.

**Next, per the operator's sequencing:** the excitability drive is null → **800 E / 200 I before any further
mechanism.** The disinhibitory (ACh-like) and theta-to-threshold drives stay held — `docs/DEFERRED.md`.

## Storage diagnostic (2026-09-21) — `storage_diagnostic/REPORT.md`

**Question.** `recall_drive` returned 0 of 18 and its frozen-weights control showed reactivation is the same with
plasticity on or off. Before any scale-up: does encoding write anything **stream-specific** into the weights?

**Design.** 200 E / 50 I, `quick.yaml`, drive off, the `recall_drive` baseline seeds (0–9) and stimuli; one recall
probe after the 120 s consolidation interval, so the post-consolidation snapshot precedes every recall cue
(encoding is identical to the baseline). Per seed: the plastic run; a plasticity-off run (null b); and 21
plasticity-frozen **replicate** runs — the stored stream plus the same 20 foreign streams used as the recall null —
with identical wiring but a **different membrane-noise stream and different auditory-nerve spikes** than the plastic
run, so the stored stream cannot win by sharing a noise realisation. From each frozen run the ΔW it *would* have
written is predicted with the network's own calcium / early-phase / protein / capture equations and correlated
with the observed ΔW over the synapses that exist. **230 runs, 0 failed, bit-reproducible.**

**Pre-registered pass** (fixed before any run, in `experiments/diagnostic.py`): on total ΔW at the pre-first-recall
snapshot, the stored stream ranks 1st of 21 in ≥ 7/10 seeds **and** beats the 95th percentile of a 1000-shuffle
permutation null in ≥ 7/10 seeds.

### Verdict: **FAIL** — stored stream ranks 1st in **0 of 10** seeds (needed ≥ 7); beats the permutation null in 10 of 10 (needed ≥ 7).

### Which case holds: **(ii) ΔW is non-zero but not stream-specific → the plasticity rule or the AHP timescale is the lead.**

Not (i): the stored stream does not rank first. Not (iii): weights change, tags are set and synapses consolidate.

### D2 — ΔW magnitudes, pre-encoding → immediately before the first recall cue (units of baseline weight h₀)

| seed | synapses | fraction changed (early / late) | mean \|ΔW\| (early / late / total) | max \|ΔW\| total | tagged (of which potentiated) | late-phase synapses | cells with protein | null (b): max \|ΔW\|, plasticity off |
|---|---|---|---|---|---|---|---|---|
| 0 | 4051 | 0.113 / 0.023 | 0.0082 / 0.0033 / 0.0115 | 0.688 | 87 (0) | 54 | 71 | 0 |
| 1 | 3917 | 0.145 / 0.038 | 0.0123 / 0.0068 / 0.0192 | 0.692 | 125 (0) | 94 | 91 | 0 |
| 2 | 3944 | 0.093 / 0.058 | 0.0158 / 0.0122 / 0.0280 | 0.703 | 206 (0) | 167 | 134 | 0 |
| 3 | 3860 | 0.152 / 0.084 | 0.0207 / 0.0170 / 0.0377 | 0.708 | 203 (0) | 254 | 152 | 0 |
| 4 | 4136 | 0.198 / 0.082 | 0.0241 / 0.0214 / 0.0455 | 0.718 | 285 (0) | 317 | 165 | 0 |
| 5 | 3900 | 0.083 / 0.055 | 0.0161 / 0.0114 / 0.0275 | 0.686 | 198 (0) | 149 | 125 | 0 |
| 6 | 3982 | 0.079 / 0.011 | 0.0039 / 0.0005 / 0.0044 | 0.620 | 38 (0) | 8 | 38 | 0 |
| 7 | 3908 | 0.113 / 0.023 | 0.0076 / 0.0024 / 0.0100 | 0.694 | 81 (0) | 70 | 75 | 0 |
| 8 | 3882 | 0.086 / 0.017 | 0.0074 / 0.0020 / 0.0094 | 0.679 | 80 (0) | 36 | 31 | 0 |
| 9 | 4074 | 0.129 / 0.031 | 0.0098 / 0.0033 / 0.0131 | 0.696 | 95 (0) | 56 | 92 | 0 |

- **Encoding writes.** 8–20 % of E→E synapses change; 38–285 are tagged; 8–317 reach the late phase; 31–165 cells
  synthesise protein. At the end of encoding the largest early-phase change is ≈ 1.0 h₀ — a synapse driven to zero.
- **It writes depression, almost only.** Of **1398 tags across the ten seeds at the post-consolidation snapshot, 0 are
  potentiation** (at the end of encoding: 1 of 1804). Mean signed ΔW is negative in both phases (early −0.013, late −0.008).
  Calcium crosses the LTD threshold (θ_d = 1.2) routinely and the LTP threshold (θ_p = 3.0) almost never at this
  network's firing rates. **This is a lead, not a fix — nothing was changed.**
- **Null (b):** with plasticity off, ΔW is **exactly 0** in every seed, both snapshots, all three components.

### D3 — rank of the stored stream among 21 (chance = 1/21; mean rank under chance = 11)

| seed | **total ΔW** (the pre-registered test): rank, r stored / best foreign | early-phase: rank, r | late-phase: rank, r | beats permutation p95 (total) |
|---|---|---|---|---|
| 0 | **4**, +0.893 / +0.909 | 3, +0.925 | 4, +0.785 | yes (p95 +0.030) |
| 1 | **12**, +0.984 / +0.989 | 10, +0.982 | 12, +0.975 | yes |
| 2 | **16**, +0.987 / +0.994 | 15, +0.986 | 16, +0.982 | yes |
| 3 | **3**, +0.986 / +0.986 | 6, +0.987 | **1**, +0.979 | yes |
| 4 | **18**, +0.986 / +0.994 | 15, +0.989 | 19, +0.979 | yes |
| 5 | **15**, +0.980 / +0.991 | 13, +0.984 | 15, +0.970 | yes |
| 6 | **19**, +0.988 / +0.997 | 20, +0.991 | 21, +0.931 | yes |
| 7 | **8**, +0.991 / +0.994 | 7, +0.990 | 7, +0.977 | yes |
| 8 | **3**, +0.960 / +0.964 | 2, +0.977 | **1**, +0.896 | yes |
| 9 | **4**, +0.973 / +0.984 | 4, +0.986 | 5, +0.906 | yes |
| | mean rank **10.2**, 1st in **0/10** | mean 9.5, 1st in 0/10 | mean 10.1, 1st in 2/10 | **10/10** |

- **Every stream predicts the written ΔW almost perfectly — including the twenty that were never played.** Foreign
  predictions correlate with the observed ΔW at r ≈ 0.96–0.99, the same as the stored stream's; stored minus mean
  foreign r is +0.006 (range −0.006 … +0.032). The stored stream's rank is scattered across 3–19, mean 10.2, which is chance.
- **So what is written is set by the network, not by the stimulus:** which synapses depress is determined by which
  cells fire hard, and that is fixed by wiring and excitability — the same conclusion the frozen-weights control
  reached for recall-phase reactivation, now reached for the weights themselves.
- **The permutation null passes 10/10 and means little here.** It shows ΔW is structured with respect to activity,
  which a stream-independent write also satisfies. The rank test is the one that answers the question, and it fails.
- Late-phase rank 1 in 2/10 seeds against ~0.5 expected is not read as a signal: those seeds' margins over the best
  foreign stream are < 0.001 in r, and the early-phase and total ranks of the same seeds are 2–6.
- **The instrument works.** Fed the plastic run's *own* activity, the offline predictor reproduces the observed ΔW
  at r = 0.999 (early), 0.983–0.999 (late), 0.998–1.000 (total). The null result is not a broken predictor.
- The end-of-encoding snapshot gives the same picture (early-phase ranks 3, 10, 15, 6, 15, 13, 20, 7, 1, 4).

**Not acted on, per instruction.** No parameter, threshold, rule or wiring was changed. `dw_arrays.npz` (observed and
stored-stream-predicted ΔW per seed) stays in the gitignored `results/` folder; everything else is in `storage_diagnostic/`.

## Built, NOT run (2026-09-21) — binaural front end; retrieval-as-writing; iterative settling

Recorded here so an absence of results is not mistaken for a null.

- **Binaural front end, MSO, neurophonic, ephaptic term** — implemented and unit-tested (commit `ae42d41f`).
  `exp binaural` was started and **stopped at the operator's instruction before completion; nothing from it was
  read or kept.** No binaural number exists in this file.
- **Retrieval-as-writing and iterative settling (C1–C8)** — implemented behind default-off switches, one commit
  per component, 50 tests, and with every switch off a committed run reproduces **bit-for-bit**.
  **`exp completion` has never been run**: the operator's precondition was that a recall-phase drive condition
  first beat the 20-foreign-stream null, and `recall_drive` gave **0 of 18**. The experiment refuses to start
  (`NEUROTAPE_ALLOW_COMPLETION=1` overrides deliberately). Its 31 conditions are declared in
  `experiments/suite.py:completion_conditions`.
- One thing found while building that bears on any future run: the **strict completion set is empty** — every
  E cell receives ~10 % of the input channels, so no cell is left undriven by even a 25 % cue. The metric falls
  back to the least-driven quartile, labelled as weaker. Sparser input connectivity would be needed for a
  clean completion test, and that is a modelling change, not a parameter to nudge.

## What the mechanisms demonstrably *did* do (so the nulls are not no-ops)

From `exp3_ablations/ENCODE_SIDE.md`: late-phase consolidation happened in **3.8 %** of E→E synapses in
the full model, **0.0 %** with tagging off and with frozen weights, and **2.5 %** with NM held flat —
the switches switch. The LOADED state occupied **17 %** of encoding. The mechanisms are engaged;
they simply do not carry a waveform.

## Caveats that change how a row should be read

- **Row 5 is a reproduction of the consolidation *logic*, not of the network's dynamics.** Core cells
  fire at the **refractory limit (500 Hz)** during the learning pulse and activity outside the core
  reaches 50–360 Hz at recall — far above the published tens of Hz. The learning-stimulus amplitude
  was taken literally from the Brian2 reference and is the likeliest cause. Also reduced N (400/100),
  in-degree-scaled θ_pro, and 60× compression instead of the authors' fast-forward. `w` at NM = 0 is
  1.29 rather than 1.0 because it is read *after* the 8 h recall pulse, which re-induces early-phase LTP.
- **Row C's negative recall (−0.107, CI below zero)** is not memory with the wrong sign; the likeliest
  reading is post-cue suppression lining up with a rising envelope. Not investigated.
- **The first pass of row 1 reported a win** (r = +0.045, "beats the ESN", identical at every delay).
  It was produced by ten seeds sharing one stimulus and a window that began inside the cue's
  carry-over. Kept at `first_pass_exp1_shared_stimulus.md` as the reason both were changed.
- **Probes share one timeline**, so an earlier probe can alter a later one.
- **Playback:** every audio file is the **vocoder fallback**. The CoNNear inversion has never run.
  Nothing has been listened to.
- **Scale:** 200 E / 50 I only. The brief's 800 / 200 was not run; "scale up only after tests pass" is
  satisfied, but with recall at zero there is no result to scale.

## What would change the picture — the cheapest next probes

1. **Ask the rate-pattern question the mechanism can answer**: decode *which stream/segment* was stored
   from recall-phase firing-rate patterns (a classification), instead of a time-locked waveform.
   Row 2's rank result says the identity information is there during encoding.
2. **Give recall something to run on** — the `no_cue` and `nm_pulse` modes have now been run (above) and
   change nothing: recall-phase firing is ~0.008 Hz in every mode, so the decoder reads silence. The next
   step is a recall-phase *drive* (disinhibition, or NM acting on E-cell excitability), with its own ablation.
3. **Fix the Lehr stimulus amplitude** against the paper's own firing-rate figure before extending it.
