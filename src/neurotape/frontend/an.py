"""Auditory-nerve front end: raw waveform -> AN spike trains.

Model: Zilany, Bruce & Carney 2014, J Acoust Soc Am 135:283 ("Updated parameters and expanded
simulation options for a model of the auditory periphery"), through the `cochlea` package
(Rudnicki, Schoppe, Isik, Volk & Hemmert 2015, Cell Tissue Res 361:159). `cochlea` is GPL-3.0:
this repository is private, and neurotape must not be redistributed with it linked in without
taking that licence on. It builds here only against Cython < 3.

Streams are MIXED ACOUSTICALLY (summed as pressure waveforms) before the cochlea, so the network
receives one nerve and has to separate the sources itself -- the AN counterpart of the filterbank
ablation's random band projection.

Low / medium / high spontaneous-rate fibres are kept as SEPARATE POPULATIONS and logged on a
tonic <-> phasic axis (``fibre_axis``): HSR fibres carry a high tonic rate and saturate early, LSR
fibres are near-silent at rest and follow level changes, so PSTH modulation depth orders them.

Efferent (MOC-like) feedback, optional: tonic NM turns cochlear gain DOWN by ``db_per_nm`` dB per
unit NM, applied to the waveform before the model. Placeholder -- see ASSUMPTIONS.md.
"""
from __future__ import annotations

import numpy as np
from scipy import signal

from ..config import Config
from .base import SpikeInput, StageUnavailable
from .io import Stream

AN_FS = 100_000.0            # zilany2014 requires 100-500 kHz
CF_MIN_HZ = 125.0            # lower limit of the human zilany2014 implementation


def _resample(x: np.ndarray, fs: float, fs_out: float) -> np.ndarray:
    if fs == fs_out:
        return x
    from fractions import Fraction
    fr = Fraction(fs_out / fs).limit_denominator(1000)
    return signal.resample_poly(x, fr.numerator, fr.denominator)


def _waveform(stream: Stream, seconds: float) -> np.ndarray:
    x = np.asarray(stream.x, float)
    n = int(round(seconds * stream.fs))
    if x.size < n:
        x = np.tile(x, int(np.ceil(n / x.size)))
    return _resample(x[:n] - x[:n].mean(), stream.fs, AN_FS)


def acoustic_mixture(streams: list[Stream], seconds: float, level_db: float,
                     only: int | None = None) -> np.ndarray:
    """Each stream set to ``level_db`` SPL on its own, then summed. ``only`` = one stream alone."""
    try:
        import cochlea
    except ImportError as e:
        raise StageUnavailable("front end 'an' needs the `cochlea` package: "
                               "uv pip install 'Cython<3' pandas && uv pip install --no-build-isolation "
                               "'cochlea @ git+https://github.com/mrkrd/cochlea.git'") from e
    parts = [cochlea.set_dbspl(_waveform(s, seconds), level_db)
             for k, s in enumerate(streams) if only is None or k == only]
    n = min(p.size for p in parts)
    return np.sum([p[:n] for p in parts], axis=0)


def run_an(sound: np.ndarray, cfg: Config, seed: int, nm_tonic: float = 0.0) -> SpikeInput:
    import cochlea
    fe = cfg.frontend
    notes = []
    if fe.moc_enabled:
        att = fe.moc_db_per_nm * nm_tonic
        sound = sound * 10 ** (-att / 20.0)
        notes.append(f"MOC-like efferent: cochlear gain -{att:.1f} dB at tonic NM {nm_tonic:g}")
    f_lo = max(fe.f_lo_hz, CF_MIN_HZ)
    if f_lo != fe.f_lo_hz:
        notes.append(f"lowest CF raised {fe.f_lo_hz:g} -> {f_lo:g} Hz (zilany2014 human limit)")
    trains = cochlea.run_zilany2014(sound, AN_FS, anf_num=tuple(fe.anf_per_cf),
                                    cf=(f_lo, min(fe.f_hi_hz, 20000.0), fe.n_bands),
                                    species="human", seed=seed)
    t, i = [], []
    for k, sp in enumerate(trains["spikes"]):
        t.append(np.asarray(sp, float)); i.append(np.full(len(sp), k, dtype=int))
    t, i = np.concatenate(t), np.concatenate(i)
    order = np.argsort(t, kind="stable")
    meta = dict(population=np.array(trains["type"], dtype=str), cf_hz=np.array(trains["cf"], float),
                modality=np.array(["audio"] * len(trains)))
    return SpikeInput(t[order], i[order], len(trains), sound.size / AN_FS, meta, "an", notes)


def fibre_axis(si: SpikeInput, bin_s: float = 0.010) -> dict[str, dict[str, float]]:
    """Tonic <-> phasic axis per fibre population: mean rate and PSTH modulation depth (sd/mean)."""
    pops = np.asarray(si.meta["population"])
    edges = np.arange(0.0, si.duration + bin_s, bin_s)
    out = {}
    for p in np.unique(pops):
        units = np.flatnonzero(pops == p)
        psth = np.histogram(si.t[np.isin(si.i, units)], edges)[0] / (units.size * bin_s)
        out[str(p)] = dict(rate_hz=float(psth.mean()),
                           modulation_depth=float(psth.std() / (psth.mean() + 1e-12)),
                           n_fibres=int(units.size))
    return out
