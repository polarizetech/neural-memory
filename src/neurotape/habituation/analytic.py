"""Deterministic (mean-field) prediction of the two-pool depression cascade under a periodic presentation train.

No network, no spikes: the fast and slow pools of each relay channel are integrated as ODEs, driven by that
channel's deterministic relay RATE for the stimulus (release rate U r xf xs), and recover between presentations
under spontaneous firing. The prediction is the stimulus-footprint-weighted efficacy E = sum_c w_c xf_c xs_c at
each presentation onset. Used to preregister SR2's slope BEFORE the network is run (docs/habituation/PREREG_S.md).

It predicts EFFICACY, not spikes. The network's spike response is a thresholded function of efficacy, so the
measured slope can differ from this one by the cells' gain nonlinearity; the report shows both.
"""
from __future__ import annotations

import numpy as np

from .config import HabConfig
from .model import a_slow_spike, steady_pools


def _integrate(xf, xs, r, dt, cfg: HabConfig):
    d = cfg.depression
    for k in range(r.shape[0]):
        rel = d.U * r[k] * xf * dt                      # expected release fraction per step (per unit xs)
        xf_new = xf + (1 - xf) * dt / d.tau_fast_s - d.U * r[k] * xf * dt
        if d.slow_on:
            dep = (a_slow_spike(cfg) * r[k] * dt) if d.slow_per == "spike" else d.a_slow * rel
            xs = xs + (1 - xs) * dt / d.tau_slow_s - dep * xs
        xf = xf_new
    return xf, xs


def _recover(x, x_star, lam, t):
    return x_star + (x - x_star) * np.exp(-lam * t)


def efficacy_train(cfg: HabConfig, rate_cf: np.ndarray, period_s: float, n: int,
                   slow_recovery_scale: float = 1.0) -> np.ndarray:
    """Efficacy at the onset of presentations 1..n (footprint-weighted, relative to channel units).
    rate_cf: (T, n_cf) relay rate of one presentation at the network dt. The gap is period - duration."""
    d, r0 = cfg.depression, cfg.periphery.relay_spont_hz
    dt = cfg.network.dt_ms * 1e-3
    dur = rate_cf.shape[0] * dt
    gap = period_s - dur
    if gap < 0:
        raise ValueError(f"period {period_s} s is shorter than the stimulus ({dur} s)")
    w = np.clip(rate_cf.mean(0) - r0, 0, None)
    w = w / w.sum()
    xf0, xs0 = steady_pools(cfg)
    xf = np.full(rate_cf.shape[1], xf0)
    xs = np.full(rate_cf.shape[1], xs0)
    lam_f = 1 / d.tau_fast_s + d.U * r0
    xf_star = (1 / d.tau_fast_s) / lam_f
    rec_s = slow_recovery_scale / d.tau_slow_s
    out = []
    for _ in range(n):
        out.append(float((w * xf * xs).sum()))
        xf, xs = _integrate(xf, xs, rate_cf, dt, cfg)
        # recovery through the gap (spontaneous release continues; the slow-pool recovery rate may be scaled)
        xf_mid = _recover(xf, xf_star, lam_f, gap / 2)
        dep = a_slow_spike(cfg) * r0 if d.slow_per == "spike" else d.a_slow * r0 * d.U * xf_mid
        lam_s = rec_s + dep
        xs = _recover(xs, rec_s / lam_s, lam_s, gap)          # lam_s > 0 always: spontaneous release never stops
        xf = _recover(xf, xf_star, lam_f, gap)
    return np.array(out)


def decrement(e: np.ndarray, last: int = 4) -> float:
    """Steady-state decrement magnitude: 1 - mean(E over the last `last` presentations) / E(presentation 1)."""
    return float(1.0 - e[-last:].mean() / e[0])


def slope_db_per_decade(rates_hz, D) -> tuple[float, float]:
    """Least-squares slope of 20 log10 D against log10 rate (dB per decade of INCREASING rate), and intercept."""
    x = np.log10(np.asarray(rates_hz, float))
    y = 20 * np.log10(np.asarray(D, float))
    b, a = np.polyfit(x, y, 1)
    return float(b), float(a)
