"""FALLBACK playback: decoded band envelopes -> audio by noise vocoding.

Output is a RECONSTRUCTION and every file written says so in its name. Nothing here is ever played
through a speaker by this code (monorepo rule: audio is verified by inspection, not by listening).
"""
from __future__ import annotations

import numpy as np
import soundfile as sf
from scipy import signal

from ..config import Frontend
from .. frontend.filterbank import _band_filter


def vocode(env_dec: np.ndarray, fcs: np.ndarray, env_scale: np.ndarray, fe: Frontend, rate_hz: float,
           fs_out: float = 16000.0, fine: np.ndarray | None = None, seed: int = 0) -> np.ndarray:
    """env_dec: (T_dec, B) compressed envelopes. ``fine`` (B, N at fs_out) re-imposes the ORIGINAL
    fine structure instead of noise carriers -- a labelled cheat, useful only as an upper bound."""
    rng = np.random.default_rng(seed)
    n = int(round(env_dec.shape[0] / rate_hz * fs_out))
    out = np.zeros(n)
    for b, fc in enumerate(fcs):
        if fc >= 0.45 * fs_out:
            continue
        e = np.clip(env_dec[:, b], 0.0, None) ** (1.0 / fe.compression) * env_scale[b]
        e = np.interp(np.arange(n) / fs_out, np.arange(e.size) / rate_hz, e)
        carrier = fine[b, :n] if fine is not None else _band_filter(rng.standard_normal(n), fc, fcs, b, fs_out, fe.filterbank)
        carrier = carrier / (np.sqrt(np.mean(carrier ** 2)) + 1e-12)
        out += e * carrier
    return 0.9 * out / (np.abs(out).max() + 1e-12)


def write_reconstruction(path, x: np.ndarray, fs: float = 16000.0) -> None:
    assert "reconstruction" in str(path), "playback files must be labelled as reconstructions"
    sf.write(str(path), x.astype(np.float32), int(fs))
