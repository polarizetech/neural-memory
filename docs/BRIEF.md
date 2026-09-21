# The commissioning brief, as given by the operator (2026-09-20), in three parts

This is the specification of record. Where the build departs from it, `ASSUMPTIONS.md` and
`CLAUDE.md` § *Not done* say so.

## Part 1

Build a Python research tool, "neurotape", that encodes several simultaneous waveforms into a
biologically grounded spiking network, stores them through synaptic tagging and capture, and plays
them back from network activity alone. Treat it as a falsification testbed, not a demo: every
mechanism must be switchable off, and every result must be compared against ablations and a plain
reservoir baseline.

**STACK** — Python 3.11, Brian2 (cpp_standalone where possible), numpy/scipy, soundfile, matplotlib,
YAML configs validated with pydantic. Read and reuse equations from
github.com/jlubo/brian_network_plasticity and github.com/jlubo/memory-consolidation-stc (Luboeinski &
Tetzlaff 2021; Lehr, Luboeinski & Tetzlaff 2022). Cite sources in code comments.

**INPUT** — CLI: `neurotape encode a.wav b.wav c.csv --config cfg.yaml`. Accept 1–N streams (WAV or
CSV, any sample rate). Front end per stream: gammatone or log-spaced band-pass filterbank (default 32
bands, 80 Hz–8 kHz; configurable down to 0.1 Hz for sensor data), Hilbert envelopes resampled to
1 kHz. Keep fine structure only for playback; the network never sees it. Mixing: each input neuron
receives a fixed sparse random projection of bands from ALL streams, so the network must separate
them itself. Provide a "labelled" debug mode with partially distinct projections.

**NEURONS** (default 800 excitatory, 200 inhibitory; start at 200/50) — Single-compartment
conductance-based model: leak, spike mechanism (AdEx or Na/K), low-threshold T-type Ca current with
voltage-dependent inactivation (Destexhe/Huguenard style), adaptation current. Log an explicit state
enum per neuron per step: REST, LOADED (hyperpolarized long enough to de-inactivate T; next
depolarization bursts), SPIKE/BURST, RESET (refractory + AHP). Unit tests: single spikes from rest;
rebound burst after a 100 ms hyperpolarizing step; burst probability increases with prior
hyperpolarization duration. Per-neuron tonic operating point: slow Ornstein-Uhlenbeck drift in bias
current (tau default 10 s).

**NEUROMODULATION** (tonic vs phasic) — Global LC-like NM(t) = tonic level (configurable, can ramp) +
phasic transients triggered by salience (mismatch between input envelope and its running average).
NM scales input gain, the protein-synthesis threshold, and the inhibitory set point.

**GAP JUNCTIONS** — Cx36-like electrical coupling among inhibitory cells (default p=0.3 within a local
neighbourhood, coupling coefficient 0.05–0.15) via Brian2 summed variables. Optional sparse E–E
coupling, OFF by default and flagged as weakly supported biologically. Coupling conductance
modulable by a pH/Mg-like scalar. Tests: measured coupling coefficient; fast spikes attenuated more
than slow potentials (low-pass behaviour).

**COMPETITION** — Lateral inhibition through the inhibitory pool, not algorithmic kWTA. For each
50 ms window, record every excitatory cell's rank by drive and whether it fired. Rank is a
first-class output, not just win/lose.

**CALCIUM, PLASTICITY, TAG AND CAPTURE** — Per-synapse calcium from pre/post spikes, with T-current
calcium adding to post; Graupner–Brunel thresholds for early LTP/LTD, as in the Luboeinski model.
Early weight h; tag set when |h − h0| > θ_tag; per-neuron protein pool driven when summed early
change exceeds θ_pro(NM); late weight z captures protein at tagged synapses. Slow per-neuron
CREB-like variable integrating somatic calcium over minutes, raising intrinsic excitability (biases
future allocation). Hours-long processes use an explicit time-compression factor (default 60x),
printed on every figure.

**STORAGE AND RECALL** — Encode streams for T seconds. Then consolidate: background noise only, NM at
a configurable tonic level, for the compressed consolidation period. Recall modes: (1) partial cue
(first 10–20% of one stream); (2) no cue, spontaneous replay under noise; (3) NM pulse only. Readout:
ridge decoder trained ONLY on encode-phase activity → per-stream band envelopes, applied unchanged
to recall activity. Noise-vocoder envelopes back to audio. Label outputs as reconstructions. Also
decode using (a) only cells that never crossed engram threshold and (b) rank bands (top 10%,
10–50%, bottom 50%).

**EXPERIMENTS** (one command each, outputs to results/<timestamp>/) — 1. One stream: reconstruction
correlation vs delay after encoding. 2. Two and three simultaneous streams: per-stream
reconstruction, crosstalk matrix, and whether stream identity is recoverable from rank position.
3. Single-mechanism ablations: no T-current, no gap junctions, flat NM, no tagging, no CREB
variable, no tonic drift. 4. Baselines: echo state network with equal unit count + linear readout;
shuffled-input control; decoder on raw input (upper bound). 5. Reproduce the Lehr et al. 2022 NM
sweep BEFORE extending it. Report mean ± 95% CI over ≥10 seeds.

**ENGINEERING** — Layout: src/neurotape/{frontend,neurons,coupling,plasticity,neuromod,recall,decode,
experiments}; pytest for every test above. ASSUMPTIONS.md listing phenomenological placeholders
(tag, protein pool, CREB variable) and every parameter's source. Scale up only after tests pass;
profile before optimising. Do not tune parameters to make recall look good. If a mechanism fails to
beat its ablation or the reservoir baseline, state that in the report.

## Part 2 — POPULATION-SIGNAL OUTPUTS

- Compute an LFP/EEG proxy (summed synaptic currents) and fit temporal response functions to the
  stimulus envelope; validate against published speech/music envelope-tracking phase-lag vs frequency.
- Option: phase-reset the theta generator on envelope onsets (entrainment) vs pure evoked responses;
  compare recall ordering under each.
- Two-stream test: attend one stream via NM gain; measure whether theta locks to it and whether its
  recall is less smeared.

## Part 3

**FRONT END** (replaces filterbank; keep filterbank as an ablation) — Audio: use the `cochlea`
package (Zilany et al. 2014) to convert raw waveforms to auditory-nerve spike trains; resample input
to the rate the model requires. Keep low/medium/high spontaneous-rate fibre types as separate
populations and log them as a tonic/phasic axis. Optional brainstem stage: cnmodel bushy/stellate
cells, and an MSO coincidence-detection stage when input is stereo. Optional efferent (MOC-like)
feedback: tonic NM scales cochlear gain. Video: pluggable retina front end (Macaque Retina Simulator
or RetinoSim) producing ON/OFF spike populations into the same core. Implement audio end-to-end
first; video is a later milestone. Core must be modality-agnostic: input is spike trains plus
metadata.

**PLAYBACK** — Primary: decode to periphery output, then invert via the differentiable CoNNear
periphery by gradient descent toward a waveform. Fallback: vocoder. Report both.

**EVALUATION ADDITIONS** — Compare stored representation size and reconstruction quality against
Opus/AAC at matched bitrate, and against event-camera encoding for video. Report honestly if the
system loses. Test salience-gated retention: does it keep a rare event from a long stream better
than uniform compression at the same storage budget?
