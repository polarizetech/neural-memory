"""Readouts for the habituation test. Nothing here feeds back into the network.

  suppression   S(x) = 1 - R_trained(x) / R_control(x), per probe x, paired (see protocol.py)
  recognition   S(stored) - mean S(novel), and the stored sound's rank among the novel null
  what is kept  S(reversed), S(shift k) against the same null: does the trace hold spectrum, order, both?
  fingerprint   "recall via habituation": the suppression pattern read against every candidate sound's
                spectral footprint -- once from the synapses directly (engram readout, a reading no animal
                could make) and once from the network's response to a flat broadband noise probe (a
                negative afterimage, the readout an animal could in principle express)
"""
from __future__ import annotations

import numpy as np

from .model import Net, Record, State


def summarise(rec: Record, stim_steps: int) -> dict:
    return dict(R=rec.e_count.sum(0).astype(float),                 # (P,) whole window
                R_onset=rec.e_count[: max(stim_steps // 8, 1)].sum(0).astype(float),
                cells=rec.cell_count.astype(float),                  # (P, NE)
                nm_peak=rec.nm.max(0))


def suppression(tr: np.ndarray, ctrl: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(ctrl > 0, 1.0 - tr / ctrl, np.nan)


def rank_of_first(scores: np.ndarray) -> tuple[int, float]:
    """scores[0] is the stored sound, the rest the novel null. Rank 1 = highest. Ties count against it.
    Returns (rank, one-sided p) with p = (1 + #null >= stored) / (1 + n_null)."""
    s0, null = scores[0], scores[1:]
    null = null[np.isfinite(null)]
    if not np.isfinite(s0) or null.size == 0:
        return -1, float("nan")
    k = int((null >= s0).sum())
    return k + 1, (1 + k) / (1 + null.size)


def efficacy_by_cf(net: Net, st: State, n_cf: int) -> np.ndarray:
    """Mean relay->E efficacy per CF (fast x slow x long-term), from the state alone. (n_cf,)"""
    cfg = net.cfg
    e = (st.xf * st.xs)[0] if cfg.depression.on else np.ones(net.n_relay)
    if st.L is not None:
        if st.L.ndim == 2:
            e = e * st.L[0]
        else:
            w = net.W0 > 0
            e = e * (st.L[0] * w).sum(1) / np.maximum(w.sum(1), 1)
    return e.reshape(n_cf, -1).mean(1)


def cell_profile(net: Net, cells_tr: np.ndarray, cells_ctrl: np.ndarray, cf: np.ndarray) -> np.ndarray:
    """Per-CF suppression of the noise-probe response, E cells binned to the nearest CF. (n_cf,)"""
    b = np.argmin(np.abs(np.log2(net.cf_e[:, None] / cf[None, :])), axis=1)
    out = np.full(cf.size, np.nan)
    for k in range(cf.size):
        m = b == k
        c = cells_ctrl[m].sum()
        if c > 0:
            out[k] = 1.0 - cells_tr[m].sum() / c
    return out


def fingerprint_rank(deficit: np.ndarray, profiles: np.ndarray) -> tuple[int, float, float]:
    """Correlate a per-CF deficit with each candidate's per-CF footprint (row 0 = stored).
    Returns (rank of stored, p, r of stored)."""
    ok = np.isfinite(deficit)
    if ok.sum() < 4 or np.nanstd(deficit[ok]) == 0:
        return -1, float("nan"), float("nan")
    r = np.array([np.corrcoef(deficit[ok], p[ok])[0, 1] if np.std(p[ok]) > 0 else np.nan for p in profiles])
    rank, pval = rank_of_first(r)
    return rank, pval, float(r[0])


def channel_L(net: Net, st: State, profile_stored: np.ndarray, frac: float = 0.2) -> dict:
    """Mean long-term factor L on the stored sound's channels vs all other channels (hebbian/presynaptic)."""
    if st.L is None:
        return {}
    n_cf = profile_stored.size
    on_cf = profile_stored > frac * profile_stored.max()
    on = np.repeat(on_cf, net.n_relay // n_cf)
    if st.L.ndim == 2:
        Lr = st.L[0]
    else:
        w = net.W0 > 0
        Lr = (st.L[0] * w).sum(1) / np.maximum(w.sum(1), 1)
    return dict(L_stored=float(Lr[on].mean()), L_other=float(Lr[~on].mean()),
                L_min_stored=float(Lr[on].min()), L_max_stored=float(Lr[on].max()))
