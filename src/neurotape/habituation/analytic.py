"""Deterministic (mean-field) prediction of the two-pool depression cascade under a presentation sequence.

No network, no spikes: the fast and slow pools of each relay channel are integrated as ODEs, driven by that
channel's deterministic relay RATE for each presentation (release rate U r xf xs), and recover between
presentations under spontaneous firing. The prediction is the footprint-weighted efficacy E = sum_c w_c xf_c xs_c
at each presentation onset, with w the footprint of the REFERENCE stimulus (the one whose response is scored).

The pools start at the spontaneous steady state of `cfg_init` (the naive network) and evolve under `cfg_run`, so a
manipulation applied at training onset (e.g. a slower slow-pool recovery, E01 SR1) is expressed by passing a
cfg_run whose `tau_slow_s` differs. `tau_slow_s = inf` is a frozen recovery.

It predicts EFFICACY, not spikes. The network's spike response is a thresholded function of efficacy, so measured
numbers can differ from these by the cells' gain nonlinearity; reports show both.
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


def efficacy_sequence(cfg_init: HabConfig, cfg_run: HabConfig, rates: list[np.ndarray], gaps_s: list[float],
                      ref_rate: np.ndarray) -> np.ndarray:
    """Efficacy (footprint of `ref_rate`) at the onset of each presentation. rates[i]: (T_i, n_cf) relay rate of
    presentation i at the network dt; gaps_s[i]: silence after presentation i (len(gaps_s) == len(rates))."""
    d, r0 = cfg_run.depression, cfg_run.periphery.relay_spont_hz
    dt = cfg_run.network.dt_ms * 1e-3
    w = np.clip(ref_rate.mean(0) - r0, 0, None)
    w = w / w.sum()
    xf0, xs0 = steady_pools(cfg_init)
    n_cf = ref_rate.shape[1]
    xf, xs = np.full(n_cf, xf0), np.full(n_cf, xs0)
    lam_f = 1 / d.tau_fast_s + d.U * r0
    xf_star = (1 / d.tau_fast_s) / lam_f
    rec_s = 1.0 / d.tau_slow_s                           # 0 when frozen (tau = inf)
    out = []
    for r, gap in zip(rates, gaps_s, strict=True):
        out.append(float((w * xf * xs).sum()))
        xf, xs = _integrate(xf, xs, r, dt, cfg_run)
        if gap < 0:
            raise ValueError("negative gap")
        xf_mid = _recover(xf, xf_star, lam_f, gap / 2)
        dep = a_slow_spike(cfg_run) * r0 if d.slow_per == "spike" else d.a_slow * r0 * d.U * xf_mid
        lam_s = rec_s + dep                              # > 0 always: spontaneous release never stops
        xs = _recover(xs, rec_s / lam_s, lam_s, gap)
        xf = _recover(xf, xf_star, lam_f, gap)
    return np.array(out)


def efficacy_train(cfg: HabConfig, rate_cf: np.ndarray, period_s: float, n: int,
                   cfg_run: HabConfig | None = None) -> np.ndarray:
    """Periodic train: n presentations of `rate_cf`, onset-to-onset `period_s`."""
    dur = rate_cf.shape[0] * cfg.network.dt_ms * 1e-3
    if period_s < dur - 1e-12:
        raise ValueError(f"period {period_s} s is shorter than the stimulus ({dur} s)")
    return efficacy_sequence(cfg, cfg_run or cfg, [rate_cf] * n, [period_s - dur] * n, rate_cf)


def decrement(e: np.ndarray, last: int = 4) -> float:
    """Steady-state decrement magnitude: 1 - mean(E over the last `last` presentations) / E(presentation 1)."""
    return float(1.0 - e[-last:].mean() / e[0])


def half_point(e: np.ndarray) -> int | None:
    """First presentation n (1-based) with E_n <= E_1 - (E_1 - E_last)/2: half of its OWN decrement."""
    thr = e[0] - 0.5 * (e[0] - e[-1])
    return next((i + 1 for i, v in enumerate(e) if v <= thr), None) if e[0] > e[-1] else None


def slope_db_per_decade(rates_hz, D) -> tuple[float, float]:
    """Least-squares slope of 20 log10 D against log10 rate (dB per decade of INCREASING rate), and intercept."""
    x = np.log10(np.asarray(rates_hz, float))
    y = 20 * np.log10(np.asarray(D, float))
    b, a = np.polyfit(x, y, 1)
    return float(b), float(a)
