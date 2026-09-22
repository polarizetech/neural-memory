# R2 — where neurotape differs from Luboeinski & Tetzlaff 2021, and every open decision

Written 2026-09-21 **before any scored R2 run**. Two unscored build tests had been made (a 200-cell smoke test and
one full-size 10 s run of seed 0, to time it: 210 s wall for 20.6 s simulated). The second showed the as-is network
near-silent at rest and Q ≈ 0 for that one seed; the difference list below was drafted before it and was not changed
by it.

## What is the paper's and what is neurotape's

**From the paper, unchanged:** 1600 E / 400 I, p = 0.1, no self-connections; only E→E plastic; every plasticity and
tagging-and-capture value of its Table 2 *network* column (preset `luboeinski2021`: c_pre 0.6, c_post 0.1655, θ_p 3.0,
θ_d 1.2, τ_c 48.8 ms, 18.8 ms calcium delay, τ_h 688.4 s, γ_p 1645.6, γ_d 313.1, σ_pl, θ_tag 0.2 h₀, τ_p = τ_z = 60 min,
α 1); τ_syn 5 ms; 3 ms axonal delay; the protocol (settle 10 s, three 0.1 s pulses at 10.0 / 10.5 / 11.0 s to 150 cells,
0.1 s cue to 75 of them, 10 s and 8 h); the metrics (0.5 s centred window, Q\*, plug-in MI against t = 11.0 s).
`gb2012_hippocampal_cal` is **not** used.

**neurotape's own, as they stand in `Config()`** — the ten differences, each removable on its own:

| key | neurotape as-is | paper |
|---|---|---|
| `adaptation` | AdEx adaptation: a = 2 nS, b = 40 pA per spike, τ_w 150 ms | none |
| `t_current` | T-type Ca current (g_T 100 nS) **and** its calcium added to every synapse's calcium (c_T 0.5) | none |
| `gaba_b` | slow GABA_B-like K⁺ conductance on I→E (1 nS, 150 ms, −95 mV) | none |
| `gap` | Cx36-like gap junctions among I cells | none |
| `slow` | slow OU drift of the operating point, 6 Hz theta pacemaker onto I cells, CREB-like excitability | none |
| `theta_pro` | θ_pro = h₀/(NM + 0.001) at tonic NM 0.12 → **8.3 h₀** (Lehr et al. 2022 form) | **0.5 h₀**, constant |
| `pl_clock` | plasticity ODEs on a 1 ms clock, neurons at 0.1 ms | one 0.2 ms step for both |
| `fast_forward` | 8 h = **480 s of full spiking**, slow terms (h decay, p, z, CREB) sped up 60× | no spiking between stimuli; slow terms integrated uncompressed |
| `inhibition` | conductance-based, w_ie = w_ii = 8 g₀ at −80 mV reversal, w_ei 2 g₀ | current-based, 4 h₀, 4 h₀, 2 h₀ |
| `lif` | the whole cell: conductance-based AdEx (C 200 pF, g_L 10 nS, E_L −70, V_T −50, Δ_T 2, reset −58 mV), background I₀ 100 pA with 60 pA SD | current-based LIF (τ 10 ms, R 10 MΩ, −65 / −55 / −70 mV), I₀ 0.15 nA, σ_wn 0.05 nA s^½ (0.5 nA SD) |

Time compression also moves the "10 s" recall: 8.9 s of simulated time after learning is 8.9 s for spikes and calcium
but 534 s for the slow terms. That is part of `fast_forward`/compression and cannot be removed separately.

## Decisions the spec left open (fixed here)

1. **Direct stimulation** is the paper's Eq. 16 as a current into neurotape's `I_inj`: an OU process, τ = τ_syn, mean
   N_stim·f_stim·w, SD w·√(N_stim·f_stim/2τ), with N_stim 25, f_stim 100 Hz and **w = one unit synapse as a current,
   g₀·(E_e − E_L) = 70 pA** (neurotape's equivalent of h₀/R = 420 pA). Mean 175 nA. As in the paper (mean 1050 nA) it
   is far above rheobase, so stimulated cells fire at their refractory limit — that is the paper's stated regime.
2. **Cued cells** = the first 75 of the 150 (the reference draws 75 at random; wiring is random, so it is a random half).
   **Shuffled cue** = cells 150–224. **Control assembly** for criterion (b) = 75 never-stimulated cells, drawn with
   `default_rng(seed + 4242)`.
3. **Two runs per seed**, identical to t = 20 s (one seed, one wiring); the 8 h run has no 10 s cue, as in the paper.
4. **Seeds 0–9.** A different random network per seed (the paper fixed one `connections.txt` and varied only the noise;
   it reports that other structures behaved the same). R1 uses the authors' fixed structure, as they did.
5. **NM** is flat at its tonic level (no envelope exists to trigger phasic release); nothing else about NM is touched.
6. **"End of learning"** for tag counts = t = 12.0 s (0.9 s after the last pulse). "After consolidation" = immediately
   before the 8 h cue. Tags are counted by sign over all E→E synapses and separately within the assembly.
7. **Cost rule for the ladder.** One full-size 8 h run is about an hour. So: `as_is` at both delays, 10 seeds. Then,
   only if it fails, every single-difference removal at the **10 s delay**, 10 seeds each (the 10 s criterion is the
   first thing to recover and costs 4 minutes a run); the 8 h delay is then run for `fast_forward` (which exists only
   at 8 h) and for whichever removals recover 10 s recall. `lif` is built only if no single removal does. Anything not
   run is reported as not run.
8. **R3 controls** (plasticity off; shuffled cue) are run on the as-is model at both delays, and again on any
   configuration that is reported as reproducing.
9. A run that errors is a failed seed and counts against (b).

## Addenda (dated; nothing above was edited)

- **2026-09-21 16:00 — like-for-like Q.** R1 showed the reference's rate read-out counts one spike twice for every active
  cell (TARGET.md, corrections). R2 therefore stores per-cell counts and reports Q both ways; criterion (a) is judged on
  `Q_ref_readout` (the reference's read-out applied to neurotape's counts), and the true-count Q is printed beside it.
  Decided after R1 and before any R2 8 h result existed; the one R2 result seen by then (as-is, 10 s) is two orders of
  magnitude from the target either way.
- **2026-09-21 16:35 — as-is failed at 10 s** (Q 0.0004 ± 0.0018), so the ladder was started. `lif` was included in it
  at once rather than held back (decision 7), because a 10 s run costs four minutes.
- **2026-09-21 17:00 — how `fast_forward` is implemented.** As the paper does it, not as a silenced simulation:
  (1) simulate to t = 20 s; (2) integrate the early-phase relaxation, protein and late-phase equations for 28 790 s with
  no spikes (`fast_forward_state`; checked against the paper's closed-form Eq. 2 to five decimals); (3) a new simulation
  of the same network from that state — 10 s re-settle, cue, read-out — with fresh noise. The rung also sets the
  time-compression factor to 1, so nothing anywhere in the run is compressed; it therefore has a 10 s variant too.
  The CREB-like variable, where present, is carried across by its own exponential decay.
- **Orphaned processes.** The first launch of the as-is stage was not killed by the restart (the CLI re-executes itself
  under another command line); its five workers ran beside the second launch for nine minutes and were then killed.
  Nothing it produced was kept.
