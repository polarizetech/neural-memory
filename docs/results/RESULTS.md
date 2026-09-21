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
