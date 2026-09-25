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


# ------------------------------------------------------------------ model-v0.2.0: pools after a schedule, per probe
# Mean-field state per CF channel: fast pool xf, slow pool xs (depression.on), surface S and internalised I receptors
# (receptor.on). Release rate per relay unit = U r xf xs (depression on) or U r (off) -- the release run() applies.
# Presentations are integrated at the network dt; silences in closed form for xf/xs and by RK4 for S/I at the
# spontaneous release rate. Predicts EFFICACY; spikes are a thresholded function of it.

def _release(cfg: HabConfig, r, xf, xs):
    d = cfg.depression
    return d.U * r * (xf * (xs if d.slow_on else 1.0) if d.on else 1.0)


def naive_pools(cfg_init: HabConfig, n_cf: int) -> dict:
    from .model import receptor_rates
    xf0, xs0 = steady_pools(cfg_init)
    st = dict(xf=np.full(n_cf, xf0), xs=np.full(n_cf, xs0))
    if cfg_init.receptor.on:
        st["S"] = np.ones(n_cf)
        st["I"] = np.full(n_cf, receptor_rates(cfg_init)["I_star"])
    return st


def _rec_derivs(cfg, S, I, rel):
    from .model import receptor_rates
    rr = receptor_rates(cfg)
    q = cfg.receptor.k_int * rel * S
    return rr["k_syn"] - rr["k_deg"] * S + rr["k_rec"] * I - q, q - (rr["k_rec"] + rr["k_deg"] + rr["k_des"]) * I


def present_pools(cfg: HabConfig, st: dict, r: np.ndarray) -> dict:
    """One presentation: r (T, n_cf) relay rate at the network dt."""
    d, dt = cfg.depression, cfg.network.dt_ms * 1e-3
    xf, xs = st["xf"].copy(), st["xs"].copy()
    S, I = st.get("S"), st.get("I")
    S = None if S is None else S.copy()
    I = None if I is None else I.copy()
    for k in range(r.shape[0]):
        rel = _release(cfg, r[k], xf, xs)
        if S is not None:
            dS, dI = _rec_derivs(cfg, S, I, rel)
            S, I = S + dS * dt, I + dI * dt
        if d.on:
            xf_new = xf + (1 - xf) * dt / d.tau_fast_s - d.U * r[k] * xf * dt
            if d.slow_on:
                dep = (a_slow_spike(cfg) * r[k] * dt * xs) if d.slow_per == "spike" else d.a_slow * rel * dt
                xs = xs + (1 - xs) * dt / d.tau_slow_s - dep
            xf = xf_new
    out = dict(xf=xf, xs=xs)
    if S is not None:
        out.update(S=S, I=I)
    return out


def silence_pools(cfg: HabConfig, st: dict, seconds: float, h: float = 2.0) -> dict:
    """Silence at spontaneous relay firing. xf/xs relax in closed form (as efficacy_sequence does); S/I by RK4."""
    if seconds < 0:
        raise ValueError("negative silence")
    d, r0 = cfg.depression, cfg.periphery.relay_spont_hz
    xf, xs = st["xf"].copy(), st["xs"].copy()
    S, I = st.get("S"), st.get("I")
    n = max(int(np.ceil(seconds / h)), 1)
    hh = seconds / n
    for _ in range(n if seconds > 0 else 0):
        if d.on:
            lam_f = 1 / d.tau_fast_s + d.U * r0
            xf_star = (1 / d.tau_fast_s) / lam_f
            xf_mid = _recover(xf, xf_star, lam_f, hh / 2)
            if d.slow_on:
                dep = a_slow_spike(cfg) * r0 if d.slow_per == "spike" else d.a_slow * r0 * d.U * xf_mid
                lam_s = 1.0 / d.tau_slow_s + dep
                xs_mid = _recover(xs, (1.0 / d.tau_slow_s) / lam_s, lam_s, hh / 2)
                xs = _recover(xs, (1.0 / d.tau_slow_s) / lam_s, lam_s, hh)
            else:
                xs_mid = xs
            xf = _recover(xf, xf_star, lam_f, hh)
            rel = d.U * r0 * xf_mid * (xs_mid if d.slow_on else 1.0)
        else:
            rel = np.full_like(xf, d.U * r0)
        if S is not None:
            q = hh / 4
            for _ in range(4):
                a1 = _rec_derivs(cfg, S, I, rel)
                a2 = _rec_derivs(cfg, S + q / 2 * a1[0], I + q / 2 * a1[1], rel)
                a3 = _rec_derivs(cfg, S + q / 2 * a2[0], I + q / 2 * a2[1], rel)
                a4 = _rec_derivs(cfg, S + q * a3[0], I + q * a3[1], rel)
                S = S + q / 6 * (a1[0] + 2 * a2[0] + 2 * a3[0] + a4[0])
                I = I + q / 6 * (a1[1] + 2 * a2[1] + 2 * a3[1] + a4[1])
    out = dict(xf=xf, xs=xs)
    if S is not None:
        out.update(S=S, I=I)
    return out


def pool_efficacy(st: dict, ref_rate: np.ndarray, r0: float) -> float:
    """Footprint-weighted efficacy of the pools for the probe whose relay rate is ref_rate (T, n_cf)."""
    w = np.clip(ref_rate.mean(0) - r0, 0, None)
    w = w / w.sum()
    e = st["xf"] * st["xs"]
    if "S" in st:
        e = e * st["S"]
    return float((w * e).sum())


def overlap(rate_a: np.ndarray, rate_b: np.ndarray, r0: float) -> float:
    """E02's overlap metric: cosine between the two probes' driven relay profiles (mean rate above spontaneous)."""
    a = np.clip(rate_a.mean(0) - r0, 0, None)
    b = np.clip(rate_b.mean(0) - r0, 0, None)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))
