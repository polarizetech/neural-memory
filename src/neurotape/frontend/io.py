"""Stream loading: WAV or CSV, any sample rate, plus synthetic demo streams."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf


@dataclass
class Stream:
    name: str
    x: np.ndarray          # 1-D float64
    fs: float              # Hz
    source: str            # path, or "synthetic:<kind>"
    lr: np.ndarray | None = None   # (2, N) when the FILE was stereo; None = mono (rendered as identical L/R)


def load_wav(path: Path) -> list[Stream]:
    x, fs = sf.read(str(path), always_2d=True, dtype="float64")
    # The mono view (x) is the channel mean and is what the mono front ends use. A stereo file also keeps
    # its two channels, which the stereo front end uses AS RECORDED (no spatialiser is applied on top).
    lr = x[:, :2].T.copy() if x.shape[1] >= 2 else None
    return [Stream(path.stem, x.mean(axis=1), float(fs), str(path), lr)]


def load_csv(path: Path, csv_rate_hz: float | None) -> list[Stream]:
    """One stream per value column. A column named t/time/seconds sets the sample rate."""
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        raise ValueError(f"{path}: empty CSV")
    try:
        [float(v) for v in rows[0]]
        header = [f"col{i}" for i in range(len(rows[0]))]
    except ValueError:
        header, rows = [h.strip() for h in rows[0]], rows[1:]
    data = np.array([[float(v) for v in r] for r in rows if r], dtype=float)
    tcol = next((i for i, h in enumerate(header) if h.lower() in ("t", "time", "seconds", "time_s")), None)
    if tcol is not None:
        t = data[:, tcol]
        dt = np.median(np.diff(t))
        if not dt > 0:
            raise ValueError(f"{path}: time column is not increasing")
        fs = 1.0 / dt
    elif csv_rate_hz:
        fs = float(csv_rate_hz)
    else:
        raise ValueError(f"{path}: no time column and frontend.csv_rate_hz is unset -- "
                         "the sample rate is not guessed")
    out = []
    for i, h in enumerate(header):
        if i == tcol:
            continue
        out.append(Stream(f"{path.stem}:{h}", data[:, i], fs, str(path)))
    return out


def load_streams(paths: list[str | Path], csv_rate_hz: float | None = None) -> list[Stream]:
    streams: list[Stream] = []
    for p in map(Path, paths):
        if p.suffix.lower() == ".csv":
            streams += load_csv(p, csv_rate_hz)
        else:
            streams += load_wav(p)
    if not streams:
        raise ValueError("no input streams")
    return streams


def synthetic_streams(n: int, seconds: float, fs: float = 16000.0, seed: int = 0) -> list[Stream]:
    """Deterministic demo streams with distinct envelope structure. SYNTHETIC, labelled as such.

    0: AM harmonic complex with a slow irregular syllable-like envelope
    1: chirp sweeps with a regular 3 Hz gate
    2: band noise bursts at irregular intervals
    """
    rng = np.random.default_rng(seed + 9173)
    t = np.arange(int(seconds * fs)) / fs
    kinds = []

    def slow_env(rate_hz, smooth_s):
        n_pts = int(seconds * rate_hz) + 2
        pts = rng.uniform(0, 1, n_pts) ** 2
        e = np.interp(t, np.arange(n_pts) / rate_hz, pts)
        k = int(smooth_s * fs)
        return np.convolve(e, np.hanning(k) / np.hanning(k).sum(), mode="same")

    f0 = 180.0
    x0 = sum(np.sin(2 * np.pi * f0 * h * t) / h for h in range(1, 12)) * slow_env(4.0, 0.08)
    kinds.append(("am_harmonic", x0))
    sweep = np.sin(2 * np.pi * (400 * t + 1800 * (t % 0.33) ** 2 / 0.66 * 3))
    x1 = sweep * (0.5 * (1 + np.sign(np.sin(2 * np.pi * 3.0 * t - 0.4)))) * slow_env(0.7, 0.3)
    kinds.append(("gated_chirp", x1))
    noise = rng.standard_normal(t.size)
    gate = np.zeros_like(t)
    tt = 0.2
    while tt < seconds:
        d = rng.uniform(0.05, 0.25)
        gate[int(tt * fs):int((tt + d) * fs)] = rng.uniform(0.4, 1.0)
        tt += d + rng.exponential(0.35)
    x2 = noise * gate
    kinds.append(("noise_bursts", x2))
    out = []
    for i in range(n):
        name, x = kinds[i % len(kinds)]
        if i >= len(kinds):  # more than three: time-reversed variants, still distinct envelopes
            x = x[::-1].copy()
            name += f"_rev{i // len(kinds)}"
        out.append(Stream(name, x / (np.abs(x).max() + 1e-12), fs, f"synthetic:{name}"))
    return out
