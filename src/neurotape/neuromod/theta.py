"""Theta pacemaker, external to the network, with optional phase reset on envelope onsets.

The contrast this exists for (Doelling, Assaneo, Bevilacqua, Pesaran & Poeppel 2019, PNAS
116:10113, "An oscillator model better predicts cortical entrainment to music"): if envelope
tracking is a train of EVOKED responses, the stimulus-response phase lag grows linearly with
stimulus frequency (a fixed latency); if an OSCILLATOR is entrained, the lag stays roughly constant.
``free`` is the evoked-only arm, ``reset`` the entrainment arm. Because onsets depend only on the
input, theta(t) is precomputed and handed to Brian2 as a TimedArray.
"""
from __future__ import annotations

import numpy as np

from ..config import Config

THETA_DT_S = 0.001


def envelope_onsets(env_mean: np.ndarray, rate_hz: float, z_thr: float, refractory_s: float) -> np.ndarray:
    """Onset times (s): upward threshold crossings of the z-scored, rectified envelope derivative."""
    k = max(int(0.02 * rate_hz), 1)
    sm = np.convolve(env_mean, np.ones(k) / k, mode="same")
    d = np.clip(np.gradient(sm) * rate_hz, 0.0, None)
    z = (d - d.mean()) / (d.std() + 1e-12)
    up = np.flatnonzero((z[1:] > z_thr) & (z[:-1] <= z_thr)) + 1
    out, last = [], -np.inf
    for i in up:
        t = i / rate_hz
        if t - last >= refractory_s:
            out.append(t); last = t
    return np.array(out)


def build_theta(cfg: Config, total_s: float, onsets_abs_s: np.ndarray, seed: int):
    """Returns (t, theta in [-1, 1], phase). ``onsets_abs_s`` are on the timeline clock."""
    th = cfg.theta
    t = np.arange(0.0, total_s + THETA_DT_S, THETA_DT_S)
    mode = th.mode if cfg.mechanisms.theta else "off"
    if mode == "off":
        return t, np.zeros_like(t), np.zeros_like(t)
    phi0 = np.random.default_rng(seed + 77).uniform(0, 2 * np.pi)
    phase = phi0 + 2 * np.pi * th.f_hz * t
    if mode == "reset":
        for to in np.sort(onsets_abs_s):
            k = int(round(to / THETA_DT_S))
            if k < t.size:
                phase[k:] = th.reset_phase_rad + 2 * np.pi * th.f_hz * (t[k:] - t[k])
    return t, np.cos(phase), np.mod(phase, 2 * np.pi)
