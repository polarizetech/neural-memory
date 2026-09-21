# CLAUDE.md — projects/neurotape

**Stage: SKETCH** (2026-09-20). A bench with no `serve.py`; not served, not listed in `served.json`.

**What it is.** A falsification testbed: encode several simultaneous waveforms into a biologically
grounded spiking network, store them through synaptic tagging and capture, and try to play them
back from network activity alone. Every mechanism has an off switch, and every result is set
beside its ablation and a plain reservoir. **The expected outcome is that it loses**, and the code
is built to say so: STC networks store *rate patterns*, not waveforms.

The commissioning prompt (three parts, as given by the operator) is in [`docs/BRIEF.md`](docs/BRIEF.md).
Parameter sources and every placeholder are in [`ASSUMPTIONS.md`](ASSUMPTIONS.md) — read it before
quoting a number.

## Result of the first full run (2026-09-21) — [`docs/results/RESULTS.md`](docs/results/RESULTS.md)

`configs/quick.yaml`, 200 E / 50 I, **10 seeds, a different stimulus per seed, 340 runs, 0 failed.**
**It does not work as a tape, and no mechanism helps.** Encoding is readable (held-out r 0.5–0.8);
recall is r ≈ 0 at every delay in every condition; every (full − ablated) CI spans zero, *including
frozen weights*; the echo state network **beats it at encoding** (0.730 vs 0.535, diff −0.195
[−0.222, −0.168]); Opus and AAC win by ~1.0 in r; salience gating shows no benefit. The mechanisms
were engaged while failing — late-phase consolidation in 3.8 % of synapses (0 % with tagging off,
2.5 % with NM flat), LOADED 17 % of encoding — so these are nulls, not no-ops.
**The one clear positive:** which stream is dominant is recoverable from **rank position** (77 % vs a
57 % permutation null, 10/10 seeds), and rank beats the binary fired vector (66 %).
**Lehr et al. 2022 sweep: 4/4 pre-registered criteria pass, qualitatively only** — core cells fire at
the refractory limit (500 Hz) under the literally-read stimulus, so it reproduces the consolidation
logic, not the network dynamics. **Population signal:** the LFP proxy follows the input at a 4 ms
latency, so the Doelling phase-concentration test is *uninformative* here and cortical ~100 ms
tracking is not reproduced; theta free vs reset left no trace.

**Follow-up — the other recall modes (30 runs, bit-reproducible):** `cue`, `no_cue` and `nm_pulse` all
fail identically; decoded recall is no closer to its own stream than to 20 foreign streams. **The NM
pulse does not wake the network, it quiets it** (it raises the inhibitory set point and gains an input
that is not there). The binding constraint is **silence** — ~13 spikes across 200 cells in 8.5 s, no
self-sustaining activity — so the next step is a recall-phase drive with its own ablation.

**Recall-phase drive, candidate 1 (NM → E-cell excitability; 180 runs + a 40-run frozen-weight control): 0 of 18
conditions and 0 of 54 condition × delay cells meet the success criterion** (~1.35 expected by chance). The drive
works as a drive — recall firing 0.008 → 0.05–29 Hz — and the reactivation score rises to +0.6, but reactivation
is **identical with frozen weights**, so it is wiring, not memory. The diagnosis moves from *nothing fires* to
*what fires carries no temporal content*. Operator's sequencing: **800 E / 200 I next, before more mechanisms**;
the ACh-like disinhibitory and theta-to-threshold drives are held in `docs/DEFERRED.md`.

## Run

```bash
cd projects/neurotape
uv venv --python 3.11 .venv && uv pip install --python .venv/bin/python -e ".[dev]" \
    -e ../../tools/universal-wave-translation-layer
# auditory-nerve front end (GPL-3, builds only against Cython < 3):
uv pip install --python .venv/bin/python "Cython<3" pandas
uv pip install --python .venv/bin/python --no-build-isolation "cochlea @ git+https://github.com/mrkrd/cochlea.git"

.venv/bin/python -m pytest -q                                  # 27 tests, ~45 s
.venv/bin/neurotape encode a.wav b.wav --config configs/default.yaml
.venv/bin/neurotape encode --demo 2 --config configs/quick.yaml   # labelled synthetic streams
.venv/bin/neurotape exp <name> --config configs/quick.yaml --seeds 10 --workers 6
#   delay streams ablations baselines lehr population attention codec salience recall_modes | all
```

Outputs: `results/<timestamp>_<name>/` — `config.yaml`, `runs.json` (every seed, including failed
ones), `summary.json`, figures stamped with the time-compression factor, `provenance.json`,
`REPORT.md`. `results/` is gitignored; the reports worth keeping are copied into `docs/results/`.

## Layout

```
src/neurotape/
  frontend/     io, filterbank (ablation + CSV route), an (Zilany 2014 via cochlea), brainstem
                (cnmodel: raises; MSO: coincidence counter), retina (interface only), mixing, encode
  neurons/      AdEx + T-type Ca + adaptation + GABA_B-like K; the REST/LOADED/SPIKE/RESET enum
  coupling/     Cx36-like gap junctions (summed variables), pH/Mg scalar
  plasticity/   calcium early phase + tagging and capture (Luboeinski & Tetzlaff 2021)
  neuromod/     NM(t) = tonic + salience-triggered phasic; attention; theta pacemaker + phase reset
  recall/       the timeline (settle → encode → [consolidate → probe]×K) and per-run evaluation
  decode/       ridge readout, ESN + raw-input baselines, LFP proxy / TRF / phase lag, vocoder, CoNNear
  experiments/  one function per experiment; mean ± 95 % CI; "beats" only if the whole CI > 0
  network.py    assembles and runs the whole timeline in ONE Brian2 build
```

## `tools/` survey (P1) — what is used and what did not fit

- **`tools/paper-library`** — both source papers and the Doelling 2019 benchmark were fetched and
  read through it. **`uwtl.surrogates.iaaft`** — the secondary null for best-lag recall.
  **`tools/result-provenance`** — stamps every results folder. **`tools/research-link`** — manifest.
- `simulators/mso-neurophonic` — a single biophysical MSO neuron with **no sodium channel**, so it
  cannot spike; the optional MSO stage here is therefore a labelled coincidence counter. Its
  `periphery.py` (Zilany 2014 through AMT under Octave) is the **fallback periphery** if `cochlea`
  stops building; not wired, because `cochlea` built.
- `simulators/betse` (tissue V_mem PDE), `tools/signal-scope` (the brief asks for matplotlib),
  `tools/injection-recovery` (its blank-trial discipline is borrowed, not imported) — do not fit.
- kept local because it is neurotape-specific — nothing else here simulates a spiking network.
  **Extraction candidates if a second consumer appears:** `decode/population.py` (LFP proxy, TRF,
  the Doelling phase-concentration test) and `experiments/storage.py:codec_roundtrip`.

## Rules the code enforces

- **An unknown config key raises.** A typo in an ablation would otherwise silently run the full model.
- **An ablation flips exactly one switch** (asserted per ablation in the tests).
- **An unavailable stage raises `StageUnavailable`; nothing falls back silently** — a run that
  quietly swapped the auditory nerve for a filterbank would be reported as something it was not.
- **The decoder is fitted on the first 80 % of the encode phase and applied unchanged to recall.**
  Its ridge penalty is chosen by blocked CV *inside encode*.
- **Playback files must be named `reconstruction_*`** (asserted at write time), and nothing is ever
  played through a speaker.
- **A mechanism "helps" only if the whole 95 % CI of (full − ablated) is above zero.** A failed seed
  is listed in the report, never dropped.
- **The time-compression factor is printed on every figure and heads every report.**

## Defects found by running it, each of which changed the code

1. **The T-current could not engage.** With GABA_A-only inhibition (reversal −80 mV) the LOADED state
   occupied **0.0000** of encoding, so the no-T-current ablation would have been a no-op reported as
   a null. A slow GABA_B-like K⁺ conductance was added; LOADED is now 13–17 %.
2. **Rank by drive was ranking the wrong thing.** Drive was a *current*, which carries `(E_e − V)`:
   inhibited, silent cells out-ranked firing ones and the top decile fired in **0.4 %** of windows
   against 7.6 % for the bottom half. Rank is by excitatory *conductance* now.
3. **A near-silent network "recalled" at p = 0.02.** Per-band IAAFT surrogates destroy the
   cross-band co-modulation of a real envelope, so any blip beat the null. The primary null is a
   circular time shift of the true envelopes; IAAFT is reported beside it.
4. **"Parallel compiles thrash" was a misdiagnosis**: six concurrent builds took 267 s each against
   20 s alone, and a build lock was added. The cause was Brian2's unbounded `-j` (see 10); the lock then
   capped throughput at ~2 jobs/min and was removed once make was bounded.
5. **BLAS oversubscription**: two pooled workers burned 1811 s of system time and took 5.5 min for
   a 27 s job. One BLAS thread per process.
6. **The LFP proxy was mostly the input arriving.** With the afferent synaptic current included it
   tracked the stimulus at **PLV 0.999 with a 7 ms lag** and came out *identical to three decimals*
   with theta free or phase-reset — it could not tell an evoked network from an entrained one. The
   primary proxy is now recurrent + inhibitory current only, and the report states whether the
   phase-concentration test is even informative at the measured latency (`pcm_is_informative`).
7. **The secondary IAAFT null cost minutes per job** in pure numpy (found by `sample`-ing a worker
   at load average 210). It is capped at 20 surrogates × 8 bands; the primary shift null is not.
8. **Reused build directories recompiled everything anyway**, because Brian2's default `TimedArray`
   names carry a process-global counter. Naming them made builds incremental (20 s → ~8 s), verified
   deterministic across reuse, across seeds and across an ablation.
9. **The first 10-seed pass reported a win that was not one.** Experiment 1 returned recall
   r = **+0.045 [+0.036, +0.052]**, "BEATS" the reservoir — and the same value at 5 min, 30 min and 2 h.
   Two faults: all ten seeds shared **one stimulus**, so anything locked to recall onset correlated
   with the same envelope every time and the CI came out falsely tight; and the window began at cue
   offset, inside the cue's own carry-over. With a different stimulus per seed and a window guarded by
   1 s, recall is **−0.03 … +0.04, CI straddling zero, does not beat the ESN**. The first report is kept
   at `docs/results/first_pass_exp1_shared_stimulus.md`.
10. **The machine-wide thrash had one cause**: Brian2's default make argument is a bare `-j`, so one
    full build launched **275 clang processes** (load average 210) and starved every running
    simulation. `extra_make_args_unix = ["-j3"]`. And each experiment's fresh worker pool meant six
    full rebuilds, so build directories are now persistent *slots* claimed by a non-blocking flock.
11. **One seed, two answers.** The same (config, seed) gave one of exactly two spike trains depending on
    the process. Not stale builds (a fresh build did it too) and not the cochlea (input spikes hashed
    identical): it is a pure function of **`PYTHONHASHSEED`** — Brian2's code generation orders terms
    by hash and `-ffast-math` rounds the orderings differently. Pinned for workers and the CLI; every
    RNG-consuming object and synaptic pathway also has an explicit scheduling order. **The first
    340-run results are unbiased but not bit-reproducible per seed.**
12. **The circular-shift null over-fires on near-silent predictions** (6/10 seeds "significant" where a
    foreign-stream null says 1/10), and is degenerate for uncued recall, where the lag search spans the
    record. `recall_modes` tests against 20 foreign streams from the same generator instead.
13. **A recall window with zero spikes crashed the best-lag statistic** (1 of 180 drive runs): a constant
    prediction makes every correlation undefined. Total silence is now a reported outcome (`silent: true`, p = 1).
14. `state` is a `StateMonitor` method, and `w` collided with the adaptation variable — both
   renamed (`nstate`, `w_syn`).

## Not done — see ASSUMPTIONS.md § "What is NOT built"

CoNNear inversion has never run (so **all playback is the vocoder fallback**); cnmodel raises; the
MSO stage is unwired; video is an interface; nothing has been listened to; nothing above
200 E / 50 I has been run; **no claim ID** — `research/` has no corpus project for this, recorded in
`BUILD-MANIFEST.md` as a gap.
