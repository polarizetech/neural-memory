"""Per-stream front end: filterbank -> Hilbert envelope -> 1 kHz.

The network only ever sees the envelopes. Fine structure (the analytic-signal phase) is kept
solely so playback can optionally re-impose it; see decode/vocoder.py.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal

from ..config import Frontend
from .io import Stream


def erb_space(f_lo: float, f_hi: float, n: int) -> np.ndarray:
    # Glasberg & Moore 1990 ERB-rate scale.
    e = lambda f: 21.4 * np.log10(4.37e-3 * f + 1.0)
    inv = lambda x: (10 ** (x / 21.4) - 1.0) / 4.37e-3
    return inv(np.linspace(e(f_lo), e(f_hi), n))


def centre_frequencies(cfg: Frontend, fs: float) -> np.ndarray:
    f_hi = min(cfg.f_hi_hz, 0.45 * fs)
    if f_hi <= cfg.f_lo_hz:
        raise ValueError(f"stream rate {fs} Hz cannot carry the band {cfg.f_lo_hz}-{cfg.f_hi_hz} Hz")
    if cfg.filterbank == "gammatone":
        return erb_space(cfg.f_lo_hz, f_hi, cfg.n_bands)
    return np.geomspace(cfg.f_lo_hz, f_hi, cfg.n_bands)


def _band_filter(x: np.ndarray, fc: float, fcs: np.ndarray, i: int, fs: float, kind: str) -> np.ndarray:
    if kind == "gammatone":
        b, a = signal.gammatone(fc, "iir", fs=fs)
        return signal.lfilter(b, a, x)
    # log-spaced Butterworth band-pass; edges at the geometric midpoints to the neighbours
    ratio = (fcs[1] / fcs[0]) if len(fcs) > 1 else 2.0
    lo, hi = fc / np.sqrt(ratio), min(fc * np.sqrt(ratio), 0.49 * fs)
    sos = signal.butter(2, [lo, hi], btype="bandpass", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, x)


@dataclass
class Analysis:
    name: str
    fs: float
    fcs: np.ndarray            # (B,)
    env: np.ndarray            # (B, T) envelopes at envelope_rate_hz, compressed, in [0, ~1]
    env_scale: np.ndarray      # (B,) normalisation applied before compression (for inversion)
    fine: np.ndarray | None    # (B, N) cos(phase) at the stream rate -- playback only
    env_rate: float


def analyse(stream: Stream, cfg: Frontend, seconds: float | None = None,
            keep_fine: bool = True) -> Analysis:
    x = np.asarray(stream.x, dtype=float)
    if seconds is not None:
        n = int(round(seconds * stream.fs))
        if x.size < n:                      # loop short streams rather than zero-pad silently
            x = np.tile(x, int(np.ceil(n / x.size)))
        x = x[:n]
    x = x - x.mean()
    fcs = centre_frequencies(cfg, stream.fs)
    n_out = int(round(x.size / stream.fs * cfg.envelope_rate_hz))
    envs, fines = [], []
    for i, fc in enumerate(fcs):
        y = _band_filter(x, fc, fcs, i, stream.fs, cfg.filterbank)
        z = signal.hilbert(y)
        e = np.abs(z)
        # smooth below half the target rate before resampling; keeps envelopes non-negative-ish
        cut = min(0.4 * cfg.envelope_rate_hz, 0.45 * stream.fs, max(fc / 2.0, 1e-3))
        sos = signal.butter(2, cut, btype="low", fs=stream.fs, output="sos")
        e = np.clip(signal.sosfiltfilt(sos, e), 0.0, None)
        e = signal.resample(e, n_out) if n_out != e.size else e
        envs.append(np.clip(e, 0.0, None))
        if keep_fine:
            fines.append(np.cos(np.angle(z)).astype(np.float32))
    env = np.array(envs)
    scale = np.percentile(env, 99, axis=1) + 1e-12
    env = np.clip(env / scale[:, None], 0.0, 1.5) ** cfg.compression
    return Analysis(stream.name, stream.fs, fcs, env, scale,
                    np.array(fines) if keep_fine else None, cfg.envelope_rate_hz)
