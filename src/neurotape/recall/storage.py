"""Storage diagnostic -- is anything stream-specific written into the weights at all?  ANALYSIS ONLY.

D2  magnitudes: what changed between the pre-encoding snapshot and a later one, early phase (h) and late
    phase (z) kept separate, in units of the baseline weight h_0 = 1.
D3  stream decode: correlate the observed dW with the dW each of 21 streams (the stored one + the same 20
    foreign streams used as the recall null) WOULD have written, predicted from that stream's own activity in
    a plasticity-frozen run by integrating the SAME calcium / early-phase / protein / capture equations the
    network uses (plasticity/stc.py), noise term omitted.
"""
from __future__ import annotations

import numpy as np

NOISE_FLOOR = 1e-6          # |dW| in units of h_0. With no threshold crossing h stays at exactly 1, so this is generous.


def snapshot(res, label: str) -> tuple[np.ndarray, np.ndarray]:
    s = res.extra["snapshots"]; k = s["labels"].index(label)
    return s["h"][:, k], s["z"][:, k]


def magnitudes(res, cfg, after: str = "pre_first_recall") -> dict:
    h0, z0 = snapshot(res, "pre_encode"); h1, z1 = snapshot(res, after)
    dh, dz = h1 - h0, z1 - z0; dw = dh + dz
    out = dict(n_synapses=int(dh.size), snapshot=after)
    for name, d in (("early", dh), ("late", dz), ("total", dw)):
        a = np.abs(d)
        out[name] = dict(frac_changed=float((a > NOISE_FLOOR).mean()), mean_abs=float(a.mean()), max_abs=float(a.max()),
                         mean_signed=float(d.mean()))
    out["n_tagged"] = int((np.abs(h1 - 1.0) > cfg.plasticity.theta_tag).sum())
    out["n_tagged_potentiated"] = int(((h1 - 1.0) > cfg.plasticity.theta_tag).sum())
    out["n_late_phase"] = int((np.abs(z1) > 0.05).sum())
    out["n_cells_protein"] = int((res.p.max(axis=1) > 0.01).sum())
    return out


# ---------------------------------------------------------------------------------------------------------- D3
def predict_dw(spk_i, spk_t, syn_i, syn_j, n_exc, cfg, nm_t, nm_v, cat_t, cat_v, enc_t0, enc_t1, horizons_s) -> dict:
    """What THIS activity would have written, by integrating the network's own plasticity equations offline on a
    1 ms grid -- the same clock the synapses run on: per-synapse calcium (pre spike after t_Ca_delay, post spike,
    plus c_T x the postsynaptic cell's T-current calcium), early-phase h with the Graupner-Brunel thresholds and
    the compressed decay, the per-cell protein pool with the NM-dependent threshold, and late-phase capture z at
    tagged synapses. The stochastic term of dh/dt is OMITTED: this is the rule's expectation, not a sample.
    After encoding no spikes are assumed (the frozen runs stop there) and the slow terms continue on a 0.1 s grid.
    Returns {horizon_label: (h - 1, z)} for each requested horizon (seconds after enc_t0)."""
    pl, F = cfg.plasticity, cfg.time_compression
    k_in = cfg.network.p_conn * cfg.network.n_exc
    th_scale = (k_in / pl.indegree_ref) if pl.scale_theta_pro_by_indegree else 1.0
    dt = 1e-3; tail = 0.5; nT = int(round((enc_t1 - enc_t0 + tail) / dt))
    rast = np.zeros((nT + 40, n_exc), dtype=np.float32)
    sel = (spk_t >= enc_t0) & (spk_t < enc_t0 + nT * dt)
    np.add.at(rast, (np.minimum(((spk_t[sel] - enc_t0) / dt).astype(int), nT - 1), spk_i[sel]), 1.0)
    d_ca = int(round(pl.t_Ca_delay_ms))
    cat = np.zeros((nT, n_exc), dtype=np.float32)
    if cat_v is not None and cfg.mechanisms.t_current:
        k0 = np.clip(np.round((enc_t0 + np.arange(nT) * dt - cat_t[0]) / dt).astype(int), 0, cat_v.shape[1] - 1)
        cat = cat_v[:, k0].T.astype(np.float32); cat[np.arange(nT) * dt >= (enc_t1 - enc_t0)] = 0.0
    ns = syn_i.size; h = np.ones(ns); z = np.zeros(ns); Ca = np.zeros(ns); p = np.zeros(n_exc)
    decay = 0.1 / (pl.tau_h_s / F); tau_p, tau_z = pl.tau_p_s / F, pl.tau_z_s / F
    a_ca = np.exp(-dt / (pl.tau_Ca_ms * 1e-3))
    nm_at = lambda t: np.interp(t, nm_t, nm_v)

    def slow(step, t_abs):
        nonlocal h, z, p
        sumd = np.bincount(syn_j, weights=np.abs(h - 1.0), minlength=n_exc)
        theta_pro = th_scale / (nm_at(t_abs) + 0.001)
        p += step * (-p + pl.alpha * (sumd > theta_pro)) / tau_p
        tp = ((h - 1.0) > pl.theta_tag) * float(cfg.mechanisms.tagging); td = ((1.0 - h) > pl.theta_tag) * float(cfg.mechanisms.tagging)
        z += step * (pl.alpha * p[syn_j] * (1 - z) * tp - pl.alpha * p[syn_j] * (z + 0.5) * td) / tau_z

    out, want = {}, sorted(horizons_s.items(), key=lambda kv: kv[1])
    for k in range(nT):
        Ca *= a_ca
        if k >= d_ca:
            Ca += pl.Ca_pre * rast[k - d_ca, syn_i]
        Ca += pl.Ca_post * rast[k, syn_j]
        tot = Ca + pl.c_T * cat[k, syn_j]
        ltp, ltd = tot > pl.theta_p, tot > pl.theta_d
        h += dt * (decay * (1.0 - h) + (pl.gamma_p * (pl.h_max - h) * ltp - pl.gamma_d * h * ltd) / pl.tau_h_s)
        slow(dt, enc_t0 + k * dt)
        while want and (k + 1) * dt >= want[0][1] - 1e-9 and want[0][1] <= nT * dt:
            out[want[0][0]] = (h - 1.0, z.copy()); out[want[0][0]] = ((h - 1.0).copy(), z.copy()); want.pop(0)
    t = nT * dt
    while want:
        target = want[0][1]
        while t < target - 1e-9:
            step = min(0.1, target - t); h += step * decay * (1.0 - h); slow(step, enc_t0 + t); t += step
        out[want[0][0]] = ((h - 1.0).copy(), z.copy()); want.pop(0)
    return out


def corr(a: np.ndarray, b: np.ndarray) -> float:
    a, b = a - a.mean(), b - b.mean(); d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 0 else float("nan")


def stream_decode(observed: np.ndarray, predicted: list[np.ndarray], n_perm: int = 1000, seed: int = 0) -> dict:
    """predicted[0] is the STORED stream, predicted[1:] the foreign ones. Rank 1 = the stored stream's prediction
    correlates best with what was actually written (ties count against it). Null (a): shuffle the observed dW
    across the existing synapses."""
    r = np.array([corr(observed, q) for q in predicted])
    if not np.isfinite(r[0]):
        return dict(defined=False, reason="observed dW or the stored prediction has no variance", r_stored=float("nan"), rank=None, r_all=r.tolist())
    rank = int(1 + np.sum(np.nan_to_num(r[1:], nan=-np.inf) >= r[0]))
    rng = np.random.default_rng(seed); q = predicted[0] - predicted[0].mean(); qn = np.sqrt((q * q).sum())
    o = observed - observed.mean(); on = np.sqrt((o * o).sum())
    null = np.array([(rng.permutation(o) * q).sum() / (on * qn) for _ in range(n_perm)])
    return dict(defined=True, r_stored=float(r[0]), rank=rank, n_streams=len(predicted), r_foreign_max=float(np.nanmax(r[1:])),
                r_foreign_mean=float(np.nanmean(r[1:])), perm_p95=float(np.percentile(null, 95)), perm_p=float((1 + (null >= r[0]).sum()) / (1 + n_perm)),
                beats_perm95=bool(r[0] > np.percentile(null, 95)), r_all=r.tolist())
