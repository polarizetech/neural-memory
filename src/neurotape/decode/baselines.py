"""Baselines every spiking result is compared against.

esn        echo state network (Jaeger 2001, GMD report 148) with the SAME unit count as the spiking
           network, driven by the SAME input spike trains (binned), read out by the SAME ridge
           protocol, and walked through the SAME timeline (encode -> silence for the delay -> cue).
           A plain reservoir has fading memory only, so whatever it scores at recall is the floor
           that "storage through plasticity" has to beat.
raw_input  the ridge decoder applied to the binned input itself: the upper bound on what any
           network fed this input could linearly hand back during encoding.
"""
from __future__ import annotations

import numpy as np

from ..config import Config
from . import readout as ro


def binned_input(si, t0_s: float, dur_s: float, rate_hz: float) -> np.ndarray:
    nT = int(round(dur_s * rate_hz))
    U = np.zeros((nT, si.n))
    sel = (si.t >= 0) & (si.t < dur_s)
    np.add.at(U, (np.minimum((si.t[sel] * rate_hz).astype(int), nT - 1), si.i[sel]), 1.0)
    return U


def esn_run(inputs, timeline, cfg: Config, n_units: int, seed: int, rho=0.9, leak=0.3, in_scale=0.5,
            noise=1e-3):
    rng = np.random.default_rng(seed + 5)
    si = inputs.spikes_enc
    W = rng.standard_normal((n_units, n_units)) * (rng.random((n_units, n_units)) < 0.1)
    W *= rho / (np.abs(np.linalg.eigvals(W)).max() + 1e-12)
    Win = rng.uniform(-in_scale, in_scale, (n_units, si.n)) * (rng.random((n_units, si.n)) < 0.1)
    rate = cfg.decode.rate_hz
    nT = int(round(timeline.total_s * rate))
    U = np.zeros((nT, si.n))
    enc = timeline.segment("encode")
    ue = binned_input(si, 0, enc.dur, rate)
    k0 = int(round(enc.t0 * rate)); U[k0:k0 + len(ue)] = ue
    for seg in timeline.recalls():
        if seg.cue_s > 0 and inputs.spikes_cue is not None:
            uc = binned_input(inputs.spikes_cue, 0, seg.cue_s, rate)
            k = int(round(seg.t0 * rate)); U[k:k + len(uc)] = uc
    U = U / (ue.std() + 1e-12)
    x = np.zeros(n_units); X = np.zeros((nT, n_units))
    for k in range(nT):
        x = (1 - leak) * x + leak * np.tanh(W @ x + Win @ U[k] + noise * rng.standard_normal(n_units))
        X[k] = x
    return X


def esn_evaluate(inputs, timeline, cfg: Config, Y: np.ndarray, seed: int) -> dict:
    rate, S = cfg.decode.rate_hz, inputs.env.shape[0]
    X = esn_run(inputs, timeline, cfg, cfg.network.n_exc + cfg.network.n_inh, seed)
    enc = timeline.segment("encode")
    k0 = int(round(enc.t0 * rate)); n = min(len(Y), int(round(enc.dur * rate)))
    Xe, Y = X[k0:k0 + n], Y[:n]
    ntr = int(cfg.decode.train_fraction * n)
    dec = ro.fit_ridge(Xe[:ntr], Y[:ntr], cfg.decode.alphas)
    out = {"encode_heldout_r": np.diag(ro.crosstalk(dec.predict(Xe[ntr:]), Y[ntr:], S)).tolist(), "recall": []}
    for seg in timeline.recalls():
        a = int(round(seg.t0 * rate)); m = min(n, int(round(seg.dur * rate)))
        c0 = int(round(seg.cue_s * rate))
        pr = dec.predict(X[a:a + m])
        g0 = c0 + int(round(1.0 * rate))
        out["recall"].append(dict(delay_s=seg.delay_s,
                                  locked_r=np.diag(ro.crosstalk(pr[c0:], Y[c0:m], S)).tolist(),
                                  guarded_r=np.diag(ro.crosstalk(pr[g0:], Y[g0:m], S)).tolist()))
    return out


def raw_input_upper_bound(inputs, cfg: Config, Y: np.ndarray) -> list[float]:
    rate, S = cfg.decode.rate_hz, inputs.env.shape[0]
    U = binned_input(inputs.spikes_enc, 0, cfg.protocol.encode_s, rate)
    a = np.exp(-1.0 / (cfg.decode.filter_tau_ms * 1e-3 * rate))
    for j in range(1, len(U)):
        U[j] += a * U[j - 1]
    n = min(len(U), len(Y)); ntr = int(cfg.decode.train_fraction * n)
    dec = ro.fit_ridge(U[:ntr], Y[:ntr], cfg.decode.alphas)
    return np.diag(ro.crosstalk(dec.predict(U[ntr:n]), Y[ntr:n], S)).tolist()
