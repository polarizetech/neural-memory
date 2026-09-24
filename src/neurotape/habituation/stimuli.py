"""Stimulus FAMILIES for the habituation tests. SYNTHETIC, labelled as such.

A sound is a small set of narrowband noise components (1/6-octave bands), each with its own slow,
syllable-like envelope. Because a sound is a *spec* (component frequencies, amplitudes, envelope and
noise seeds), controlled relatives can be rendered from it:

  same         identical waveform (the probe for the stored sound; fresh relay spikes every time)
  reversed     the waveform time-reversed: identical long-term spectrum, reversed temporal order
  shift(k)     every component moved by k octaves, envelopes and noise seeds unchanged
  novel        an independent draw from the same generator (the foreign-stimulus null)

These let the recognition readout say WHAT a habituation trace keeps: if `reversed` looks exactly as
familiar as `same`, the trace holds the spectrum and not the temporal order.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
from scipy import signal

FS = 16000.0


@dataclass(frozen=True)
class SoundSpec:
    name: str
    freqs_hz: tuple[float, ...]
    amps: tuple[float, ...]
    env_seeds: tuple[int, ...]
    noise_seed: int
    dur_s: float
    reverse: bool = False
    shift_oct: float = 0.0
    level_db: float | None = None           # None = the periphery's neutral level
    kind: str = "sound"                     # "sound" | "noise" (broadband probe) | "silence"


def draw(rng: np.random.Generator, name: str, dur_s: float, n_comp: int = 4,
         f_lo: float = 300.0, f_hi: float = 4500.0) -> SoundSpec:
    """Component centres log-uniform in [f_lo, f_hi], at least 1/3 octave apart."""
    for _ in range(1000):
        f = np.sort(np.exp(rng.uniform(np.log(f_lo), np.log(f_hi), n_comp)))
        if np.all(np.diff(np.log2(f)) >= 1 / 3):
            break
    else:                                    # pragma: no cover
        raise RuntimeError("could not place components")
    amps = rng.uniform(0.5, 1.0, n_comp)
    return SoundSpec(name, tuple(map(float, f)), tuple(map(float, amps)),
                     tuple(int(s) for s in rng.integers(0, 2**31, n_comp)), int(rng.integers(0, 2**31)), dur_s)


def variant(spec: SoundSpec, kind: str, arg: float = 0.0) -> SoundSpec:
    if kind == "same":
        return spec
    if kind == "reversed":
        return replace(spec, name=spec.name + "_rev", reverse=True)
    if kind == "shift":
        return replace(spec, name=f"{spec.name}_shift{arg:+.3f}oct", shift_oct=arg)
    raise ValueError(kind)


def louder(spec: SoundSpec, db: float, base_db: float) -> SoundSpec:
    return replace(spec, name=f"{spec.name}_+{db:g}dB", level_db=base_db + db)


def noise_probe(dur_s: float, seed: int = 424242) -> SoundSpec:
    return SoundSpec("broadband_noise_probe", (), (), (), seed, dur_s, kind="noise")


def silence(dur_s: float) -> SoundSpec:
    return SoundSpec("silence", (), (), (), 0, dur_s, kind="silence")


def _slow_env(n: int, rng: np.random.Generator, rate_hz: float = 4.0, smooth_s: float = 0.06) -> np.ndarray:
    dur = n / FS
    k = int(dur * rate_hz) + 2
    pts = rng.uniform(0.0, 1.0, k) ** 2
    e = np.interp(np.arange(n) / FS, np.arange(k) / rate_hz, pts)
    w = np.hanning(max(int(smooth_s * FS), 3))
    return np.convolve(e, w / w.sum(), mode="same")


def render(spec: SoundSpec) -> np.ndarray:
    """Waveform at FS, unit peak (level is applied by the periphery). Ends ramped 10 ms."""
    n = int(round(spec.dur_s * FS))
    if spec.kind == "silence":
        return np.zeros(n)
    if spec.kind == "noise":
        x = np.random.default_rng(spec.noise_seed).standard_normal(n)
    else:
        noise_rng = np.random.default_rng(spec.noise_seed)
        x = np.zeros(n)
        for f, a, es in zip(spec.freqs_hz, spec.amps, spec.env_seeds, strict=True):
            fc = f * 2.0 ** spec.shift_oct
            lo, hi = fc * 2 ** (-1 / 12), min(fc * 2 ** (1 / 12), 0.45 * FS)
            sos = signal.butter(4, [lo, hi], btype="bandpass", fs=FS, output="sos")
            band = signal.sosfilt(sos, noise_rng.standard_normal(n))
            band /= np.sqrt(np.mean(band ** 2)) + 1e-12
            x += a * band * _slow_env(n, np.random.default_rng(es))
        if spec.reverse:
            x = x[::-1].copy()
    r = int(0.01 * FS)
    ramp = np.ones(n); ramp[:r] = np.linspace(0, 1, r); ramp[-r:] = np.linspace(1, 0, r)
    x = x * ramp
    return x / (np.abs(x).max() + 1e-12)


@dataclass
class Family:
    stored: SoundSpec
    relatives: dict[str, SoundSpec]         # "reversed", "shift+0.167oct", ...
    novel: list[SoundSpec]                  # the foreign-stimulus null
    interference: list[SoundSpec]           # played during the delay; never probed
    noise: SoundSpec


def family(seed: int, dur_s: float, n_novel: int, shifts_oct: list[float], n_interf: int = 8) -> Family:
    rng = np.random.default_rng(seed + 55_001)
    stored = draw(rng, "stored", dur_s)
    rel = {"reversed": variant(stored, "reversed")}
    for k in shifts_oct:
        rel[f"shift{k:+.3f}oct"] = variant(stored, "shift", k)
    novel = [draw(rng, f"novel{j:02d}", dur_s) for j in range(n_novel)]
    interf = [draw(rng, f"interf{j:02d}", dur_s) for j in range(n_interf)]
    return Family(stored, rel, novel, interf, noise_probe(dur_s))
