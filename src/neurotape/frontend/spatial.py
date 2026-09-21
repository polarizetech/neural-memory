"""Spatialiser: render a mono stream at an azimuth by imposing an ITD and an ILD. NOT an HRTF.

ITD   Woodworth's rigid-sphere formula, ITD = (a/c)(theta + sin theta), a = 8.75 cm, c = 343 m/s: 0 at the
      midline and ~656 us at 90 degrees, inside this monorepo's 660 us ceiling (asserted). Applied as a
      FINE-STRUCTURE delay of the whole waveform (a linear phase ramp), half to each ear.
ILD   a smooth frequency-dependent shelf, ILD(f) = ild_max_db * sin(az) * f^2 / (f^2 + f_c^2): near zero
      at low frequency, approaching ild_max_db above a few kHz. This is a PLACEHOLDER for the shape of a
      head shadow, not a measurement; no pinna cues, no elevation, no distance. HRTF rendering is the
      stated upgrade path and is not built.
Positive azimuth = source to the RIGHT: the right ear leads and is louder.
"""
from __future__ import annotations

import numpy as np

HEAD_RADIUS_M, C_SOUND = 0.0875, 343.0
ITD_CEILING_US = 660.0


def woodworth_itd_s(azimuth_deg: float) -> float:
    th = np.deg2rad(np.clip(azimuth_deg, -90.0, 90.0))
    itd = HEAD_RADIUS_M / C_SOUND * (th + np.sin(th))
    assert abs(itd) * 1e6 <= ITD_CEILING_US, "ITD beyond the 660 us ceiling"
    return float(itd)


def ild_db(f_hz: np.ndarray, azimuth_deg: float, ild_max_db: float = 20.0, corner_hz: float = 1500.0) -> np.ndarray:
    return ild_max_db * np.sin(np.deg2rad(azimuth_deg)) * f_hz ** 2 / (f_hz ** 2 + corner_hz ** 2)


def spatialise(x: np.ndarray, fs: float, azimuth_deg: float, ild_max_db: float = 20.0, corner_hz: float = 1500.0,
               itd_s: float | None = None, apply_ild: bool = True) -> np.ndarray:
    """Returns (2, N): row 0 = LEFT, row 1 = RIGHT. azimuth 0 returns two identical channels exactly."""
    itd = woodworth_itd_s(azimuth_deg) if itd_s is None else float(itd_s)
    if itd == 0.0 and (azimuth_deg == 0.0 or not apply_ild):
        return np.stack([x, x]).astype(float)
    X = np.fft.rfft(x); f = np.fft.rfftfreq(x.size, 1.0 / fs)
    g = ild_db(f, azimuth_deg, ild_max_db, corner_hz) / 2.0 if apply_ild else np.zeros_like(f)
    left = X * np.exp(-2j * np.pi * f * (+itd / 2.0)) * 10 ** (-g / 20.0)     # source right -> left lags, quieter
    right = X * np.exp(-2j * np.pi * f * (-itd / 2.0)) * 10 ** (+g / 20.0)
    return np.stack([np.fft.irfft(left, x.size), np.fft.irfft(right, x.size)])
