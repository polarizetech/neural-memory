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


# ----------------------------------------------------------------------------------------------------------
# The WIRED stage: a coincidence population with synaptic currents, and the neurophonic they generate.
# ----------------------------------------------------------------------------------------------------------
from dataclasses import dataclass

MSO_FS = 50_000.0            # 20 us grid: internal delays are multiples of 100 us = 5 samples


@dataclass
class Neurophonic:
    """The MSO neurophonic, computed from POSTSYNAPTIC CURRENTS, never from spikes. Basis: Goldwyn, Mc Laughlin,
    Verschooten, Joris & Rinzel 2014, J Neurosci 34(35):11705 -- their model takes postsynaptic current flow as
    the dominant generator of the field and finds spikes contribute negligibly. Units: EPSC units summed over
    the population, per unit -- a shape, not microvolts (there is no geometry here)."""
    t0_s: float
    fs: float
    total: np.ndarray            # sum over every MSO unit of (ipsi EPSC + contra EPSC - IPSC)
    per_delay: np.ndarray        # (n_delays, T): the same, summed over CF only
    delays_us: np.ndarray


def _alpha(tau_s: float, fs: float) -> np.ndarray:
    t = np.arange(0.0, 8 * tau_s, 1.0 / fs)
    k = t / tau_s * np.exp(1.0 - t / tau_s)
    return k


def mso_population(left: SpikeInput, right: SpikeInput, cfg, seed: int = 0, keep_fs: float = 5000.0):
    """One MSO (ipsilateral = LEFT). Each unit = (characteristic frequency, characteristic delay). It receives
    ipsilateral excitation, contralateral excitation through its internal delay, and FAST CONTRALATERAL
    GLYCINERGIC INHIBITION that arrives `inh_lead_ms` before the contralateral excitation (the MNTB pathway;
    Grothe 2003 Nat Rev Neurosci 4:540 for the arrangement -- cited from memory). A leaky membrane integrates the
    currents and fires on threshold. Only CF <= cf_max_hz: above the phase-locking limit there is no
    fine-structure ITD to detect (Verschooten et al. 2019, Hear Res 377:109). ENVELOPE ITD at higher carriers
    is OUT OF SCOPE here and is not modelled.  Returns (SpikeInput, Neurophonic)."""
    from scipy.signal import fftconvolve
    m = cfg.mso
    if max(abs(d) for d in m.delays_us) > ITD_CEILING_US:
        raise ValueError(f"internal delay exceeds the {ITD_CEILING_US:g} us ITD ceiling")
    dur = max(left.duration, right.duration); nT = int(np.ceil(dur * MSO_FS)) + 1
    cfs = np.asarray(left.meta["cf_hz"]); ftype = np.asarray(left.meta.get("fibre_type", left.meta["population"]))
    use_cf = np.unique(cfs[cfs <= m.cf_max_hz])
    ke, ki, km = _alpha(m.tau_e_ms * 1e-3, MSO_FS), _alpha(m.tau_i_ms * 1e-3, MSO_FS), np.exp(-np.arange(0, 8 * m.tau_m_ms * 1e-3, 1 / MSO_FS) / (m.tau_m_ms * 1e-3))
    km = km / km.sum()
    epsp_peak = float(np.convolve(ke, km).max())
    dec = int(round(MSO_FS / keep_fs)); nK = nT // dec
    total, per_delay = np.zeros(nK), np.zeros((len(m.delays_us), nK))
    lead = int(round(m.inh_lead_ms * 1e-3 * MSO_FS)); ref = int(round(m.t_ref_ms * 1e-3 * MSO_FS))
    t_out, i_out, meta_cf, meta_d, unit = [], [], [], [], 0

    def train(si, sel):
        h = np.bincount(np.minimum((si.t[np.isin(si.i, sel)] * MSO_FS).astype(int), nT - 1), minlength=nT).astype(float)
        return h

    def shift(a, n):
        out = np.zeros_like(a)
        if n >= 0:
            out[n:] = a[:a.size - n] if n else a
        else:
            out[:n] = a[-n:]
        return out
    for cf in use_cf:
        sel = np.flatnonzero((cfs == cf) & np.isin(ftype, ("hsr", "msr")))
        hL, hR = train(left, sel), train(right, sel)
        eL, eR, iR = fftconvolve(hL, ke)[:nT], fftconvolve(hR, ke)[:nT], fftconvolve(hR, ki)[:nT]
        for kd, d in enumerate(m.delays_us):
            n = int(round(d * 1e-6 * MSO_FS))
            cur = eL + shift(eR, n) - m.w_inh * shift(iR, n - lead)          # the POSTSYNAPTIC CURRENT
            dcur = cur[:nK * dec].reshape(nK, dec).mean(axis=1)
            total += dcur; per_delay[kd] += dcur
            v = fftconvolve(cur, km)[:nT]
            up = np.flatnonzero((v[1:] >= m.theta_epsp * epsp_peak) & (v[:-1] < m.theta_epsp * epsp_peak)) + 1
            keep, last = [], -ref
            for k in up:
                if k - last >= ref:
                    keep.append(k); last = k
            t_out.append(np.array(keep) / MSO_FS); i_out.append(np.full(len(keep), unit, dtype=int))
            meta_cf.append(cf); meta_d.append(d); unit += 1
    t = np.concatenate(t_out) if t_out else np.array([]); i = np.concatenate(i_out) if i_out else np.array([], dtype=int)
    order = np.argsort(t, kind="stable")
    meta = dict(population=np.array(["mso"] * unit, dtype=str), cf_hz=np.array(meta_cf, float),
                best_delay_us=np.array(meta_d, float), modality=np.array(["audio"] * unit), ear=np.array(["B"] * unit),
                fibre_type=np.array(["mso"] * unit))
    si = SpikeInput(t[order], i[order], unit, dur, meta, "mso",
                    ["MSO: one side only (ipsi = LEFT); leaky coincidence units, not a biophysical MSO cell",
                     f"MSO input limited to CF <= {m.cf_max_hz:g} Hz; envelope ITD at higher carriers is out of scope"])
    return si, Neurophonic(0.0, keep_fs, total / max(unit, 1), per_delay / max(len(use_cf), 1), np.array(m.delays_us, float))
