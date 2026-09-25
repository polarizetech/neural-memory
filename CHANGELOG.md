# CHANGELOG — the `neurotape` model

`src/neurotape/` is this repo's `model/` (PREREG_PROTOCOL.md §1). A change to it that alters numerical output
bumps `model-vX.Y.Z`, and each entry says which experiments it invalidates. Tags are made with
`.agents/tools/tag`, never bare `git tag`.

## model-v0.4.0 — 2026-09-25

Two switches in `neurotape.singlecell`, both defaulting to the published model (the default Antimony text is
byte-identical to model-v0.3.0; tested), plus a reusable gate. For E03.

- `recycling="labile"`: recycling of internalised receptors runs at k_rec·X, where X is a short-lived,
  synthesis-dependent factor (dX/dt = k_x(syn − X), X = 1 at rest, k_x default 1/60 min⁻¹). Without a block X stays
  at 1 and the model is the published one (to integrator tolerance, ~1e-5). Motivated by Rajan et al. 2026
  (doi 10.1016/j.cub.2026.03.080), whose authors propose that recovery requires new protein synthesis.
- `k_deg_scale`: scales basal turnover k_deg and synthesis k_syn together, so S* = 35 is unchanged.
- `gate.py`: the R1–R8 reproduction checks as functions of any `CellConfig`; the tests call them on the published model.
- Invalidates: nothing (defaults unchanged; no committed experiment uses `neurotape.singlecell`).

## model-v0.3.0 — 2026-09-25

New package `neurotape.singlecell`, nothing else changed (every existing module and committed run untouched).

- Rajan & Marshall 2025's Stentor receptor-inactivation model, reimplemented from their Methods and MATLAB (v9) with
  their published parameters; continuous dynamics in Antimony, integrated by libRoadRunner (Tellurium); stimulus jumps
  applied as in the authors' code. Time in minutes.
- Reproduction gate (`tests/test_singlecell.py`, R1–R8): habituation and recovery, no dishabituation, force dependence,
  the hidden variable, interleaved weak/strong, subliminal accumulation, frequency dependence, no rate sensitivity --
  all reproduced with the published parameters and every switch off.
- Switches, each defaulting to the published model: `n_channels` (independent receptor pools per modality),
  `mechanism="gating"` (Wood 1988: receptors modified in place, not internalised or destroyed), `synthesis_scale`
  from `block_from_min` (protein-synthesis block).
- `export.py`: one self-describing JSON per run (tier MODELLED, source, config, protocol, traces, events, a seeded
  sampled cell) for the viewer.
- Dependency: optional extra `singlecell` = tellurium. Installing it upgraded numpy to 2.x once; numpy was pinned
  back to 1.26.4 and every E01/E02 `ENV.lock` pin still matches (checked).
- Invalidates: nothing.

## Unreleased — 2026-09-25 (no numerical change; no model tag)

Pre-release review and lint (`docs/REVIEW.md`). Nothing here changes any number a committed run produced, so no
`model-v*` bump; but `src/` now differs from `model-v0.2.0`, so re-running E01/E02 through their gated `run.py`
needs `git checkout` of the experiment's model tag first.

- `ruff` (correctness rules only) added to `pyproject.toml` and the dev extra; 79 findings resolved: unused imports
  removed, `zip(..., strict=True)` where lengths must match, `itertools.pairwise`, narrowed test exceptions.
- `experiments/common.paired_diff` raises on unequal lengths instead of truncating (a failed seed would have
  misaligned every later pair; no committed paired condition had one).
- `decode/readout.bestlag_with_null`: without the private `uwtl`, the secondary IAAFT null is skipped and recorded
  (`p_iaaft: null`, `iaaft_skipped`); with it, behaviour is unchanged.
- `tests/test_monorepo.py` skips when the private monorepo is absent.
- Known and NOT fixed (each would change future numbers): recall-delay bookkeeping (`recall/protocol.py`), the
  Hebbian factor's off-steady-state start (`habituation/model.py`), the settle crash for plastic FF inhibition.

## model-v0.2.0 — 2026-09-24

E02 mechanisms, every one default OFF; switched-off output unchanged (bit-for-bit below).

- `habituation.config.FFInh` + model: a feedforward-inhibitory pathway relay → FF (tonotopic LIF) → E, with an
  optional plastic multiplier G under the inhibitory STDP rule of Vogels et al. 2011 (α = 2ρ0τ, ρ0 = the measured
  spontaneous E rate; G relaxes to g0 with τ_s). Built on its own RNG stream, so the E network is identical with
  it on or off.
- `habituation.config.Receptor` + model: Rajan & Marshall 2025 receptor inactivation (surface / internalised
  pools, recycling, basal degradation, destruction, synthesis with `synthesis_scale`) per relay fibre; rates read
  per minute; k_syn derived for S = 1 at spontaneous release.
- `State.ff_out` (pathway removal), `State.g_in` (global relay→E gain), `run(..., keep_cells=True)` (per-cell
  spike rasters), `Record.ff_count`.
- `Sim.fast_forward`: G relaxation and RK4 receptor pools. Found while building it: `fast_forward` and
  `spont_release` use U = 1 with depression off while `run()` releases U per spike. Left as is (the Hebbian
  fast-forward is self-consistent with it and v0.1.0 results depend on it); the receptor code uses the release
  `run()` applies.
- `habituation.analytic`: `naive_pools`, `present_pools`, `silence_pools`, `pool_efficacy` (depression and
  receptor pools after any schedule, per probe footprint) and `overlap` (E02's overlap metric).
- Tests: `tests/test_habituation_v02.py`, 10 new.
- **Bit-for-bit:** every committed habituation `runs.json` (hab_isi 30, hab_memory 50, hab_salience 70,
  sweep_eta_x0.25 20, sweep_eta_x4 20, EXPLORATORY_slow_per_spike 20 = 210 job records; v0.1.0's entry counted these
  as "260 runs") and E01-stentor-map's sr1/sr2/sr3 (90) re-run byte-identically under this code before tagging.
  Full suite: 100 passed.
- Invalidates: nothing.

## model-v0.1.0 — 2026-09-24

Habituation steps 1–3 + analytic.py; 260/260 bit-for-bit.

- Everything built as `projects/neurotape` in the audio-projects monorepo up to 4272203d, split out here with its
  history: the tagging-and-capture model and its experiments, the Luboeinski & Tetzlaff 2021 reproduction, and the
  minimal habituation model (`neurotape.habituation`) with preregistered steps 1–3.
- `habituation/analytic.py`: the deterministic two-pool cascade prediction. Extended before this tag to
  presentation sequences and to a recovery change applied at training onset. Nothing that produced a committed
  result calls it.
- Shared tools reached through `neurotape/monorepo.py` (no numerical effect).
- `protocol.fast_forward`: a frozen recovery (τ = ∞) with zero erosion put NaN into L (0/0); now L stays put
  (commit 7b14028). **Found by the E01-stentor-map smoke run** (plumbing check on a throwaway configuration, flags
  only), before this tag. Unreachable with any finite recovery time, so no committed result is affected.
- **Bit-for-bit:** all 260 habituation runs (hab_memory, hab_salience, hab_isi, both eta sweeps, the exploratory
  per-spike arm) reproduced byte-identically — in the monorepo at e5ad2a81, and again in this repo before tagging.
  The tagging-and-capture experiments were not re-run for this tag; their 50 unit tests pass.
- Invalidates: nothing (first tag).
