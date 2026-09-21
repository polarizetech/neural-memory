"""Optional stages between the nerve and the core. Both are OFF by default.

cnmodel  Manis & Campagnola 2018, Hear Res 360:76 -- biophysical bushy / T-stellate cells. It needs
         NEURON and is not installed here; asking for it raises StageUnavailable with the install
         line rather than silently passing AN spikes through under a brainstem label.
mso      A PHENOMENOLOGICAL coincidence stage for stereo input: per low-CF channel, a unit fires
         when a left and a right HSR spike arrive within ``window_us`` after an internal delay. It is
         a Jeffress-style counter, not a membrane model -- the biophysical MSO in this monorepo
         (simulators/mso-neurophonic, Goldwyn et al. 2014) has no sodium channel and cannot spike,
         which is why it is not used here. Internal delays respect the monorepo's 660 us ITD ceiling.
"""
from __future__ import annotations

import numpy as np

from .base import SpikeInput, StageUnavailable

ITD_CEILING_US = 660.0       # Woodworth head-size limit used across this monorepo
MSO_CF_MAX_HZ = 1500.0       # fine-structure ITD coding band


def cn_stage(si: SpikeInput) -> SpikeInput:
    try:
        import cnmodel  # noqa: F401
    except ImportError as e:
        raise StageUnavailable("brainstem stage 'cnmodel' needs NEURON + cnmodel "
                               "(pip install neuron cnmodel); it is not installed on this bench") from e
    raise StageUnavailable("cnmodel is importable but the bushy/stellate wiring is not built yet")


def mso_stage(left: SpikeInput, right: SpikeInput, window_us: float = 100.0,
              delays_us=(-600, -300, 0, 300, 600)) -> SpikeInput:
    if max(abs(d) for d in delays_us) > ITD_CEILING_US:
        raise ValueError(f"internal delay exceeds the {ITD_CEILING_US:g} us ITD ceiling")
    pops, cfs = np.asarray(left.meta["population"]), np.asarray(left.meta["cf_hz"])
    use_cf = np.unique(cfs[(cfs <= MSO_CF_MAX_HZ)])
    t_out, i_out, meta_cf, meta_delay = [], [], [], []
    w = window_us * 1e-6
    unit = 0
    for cf in use_cf:
        sel = np.flatnonzero((cfs == cf) & (pops == "hsr"))
        tl = np.sort(left.t[np.isin(left.i, sel)])
        tr = np.sort(right.t[np.isin(right.i, sel)])
        for d in delays_us:
            shifted = tr + d * 1e-6
            k = np.searchsorted(shifted, tl)
            near = np.minimum(np.abs(shifted[np.clip(k, 0, shifted.size - 1)] - tl),
                              np.abs(shifted[np.clip(k - 1, 0, shifted.size - 1)] - tl)) if shifted.size else np.full(tl.size, np.inf)
            hits = tl[near <= w]
            t_out.append(hits); i_out.append(np.full(hits.size, unit, dtype=int))
            meta_cf.append(cf); meta_delay.append(d); unit += 1
    t = np.concatenate(t_out) if t_out else np.array([])
    i = np.concatenate(i_out) if i_out else np.array([], dtype=int)
    order = np.argsort(t, kind="stable")
    meta = dict(population=np.array(["mso"] * unit, dtype=str), cf_hz=np.array(meta_cf, float),
                best_delay_us=np.array(meta_delay, float), modality=np.array(["audio"] * unit))
    return SpikeInput(t[order], i[order], unit, left.duration, meta, "an+mso",
                      ["MSO stage is a phenomenological coincidence counter, not a membrane model"])


def concat(a: SpikeInput, b: SpikeInput) -> SpikeInput:
    meta = {}
    for k in set(a.meta) | set(b.meta):
        fill = lambda m, n: np.asarray(m.get(k, np.full(n, np.nan if k.endswith(("hz", "us")) else "")))
        meta[k] = np.concatenate([fill(a.meta, a.n), fill(b.meta, b.n)])
    return SpikeInput(np.concatenate([a.t, b.t]), np.concatenate([a.i, b.i + a.n]), a.n + b.n,
                      max(a.duration, b.duration), meta, f"{a.front_end}+{b.front_end}", a.notes + b.notes)
