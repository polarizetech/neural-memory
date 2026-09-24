# CHANGELOG — the `neurotape` model

`src/neurotape/` is this repo's `model/` (PREREG_PROTOCOL.md §1). A change to it that alters numerical output
bumps `model-vX.Y.Z`, and each entry says which experiments it invalidates. Tags are made with
`.agents/tools/tag`, never bare `git tag`.

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
