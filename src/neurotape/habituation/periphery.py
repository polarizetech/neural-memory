"""Sound -> per-CF RELAY rate (Hz) at the network time step.

The habituating synapses sit on the RELAY -> cortex-like connection, not on the auditory nerve itself.
Auditory-nerve high-spontaneous fibres fire 50-100 spikes/s in silence; a depressing synapse driven by
that would spend its whole life depleted by silence. The relay stage stands in for the thalamic
(MGB-like) input to A1, which has a low spontaneous rate. It is PHENOMENOLOGICAL: the pooled AN rate per
CF, minus its own spontaneous rate, rectified and scaled. MGB is not a subtraction; this is a labelled
placeholder (ASSUMPTIONS.md).

  kind "an"   : Zilany, Bruce & Carney 2014 via `cochlea` (PRIMARY). Raises StageUnavailable if absent --
                it never falls back to "rate" on its own.
  kind "rate" : gammatone band envelope -> level in dB SPL -> sigmoid rate-level function. A labelled
                rate model, for tests and for machines without `cochlea`.
"""
from __future__ import annotations

import numpy as np
from scipy import signal

from ..frontend.base import StageUnavailable
from .config import HabConfig
from .stimuli import FS, SoundSpec, render

AN_FS = 100_000.0
P_REF = 20e-6


def cf_grid(cfg: HabConfig) -> np.ndarray:
    p = cfg.periphery
    return np.geomspace(p.f_lo_hz, p.f_hi_hz, p.n_cf)


def _level_scale(x: np.ndarray, level_db: float) -> np.ndarray:
    rms = np.sqrt(np.mean(x ** 2))
    return x * (P_REF * 10 ** (level_db / 20) / rms) if rms > 0 else x


def _smooth(r: np.ndarray, dt: float, ms: float) -> np.ndarray:
    k = max(int(round(ms * 1e-3 / dt)), 1)
    if k == 1:
        return r
    w = np.hanning(2 * k + 1); w /= w.sum()
    return np.apply_along_axis(lambda v: np.convolve(v, w, mode="same"), 0, r)


class Periphery:
    """Caches one relay-rate matrix per (spec, level). Relay SPIKES are drawn fresh per presentation."""

    def __init__(self, cfg: HabConfig):
        self.cfg = cfg
        self.cf = cf_grid(cfg)
        self.dt = cfg.network.dt_ms * 1e-3
        self._cache: dict = {}
        self._an_spont = None
        if cfg.periphery.kind == "an":
            try:
                import cochlea  # noqa: F401
            except ImportError as e:
                raise StageUnavailable("habituation periphery 'an' needs the `cochlea` package (see CLAUDE.md "
                                       "Run); set periphery.kind: rate explicitly to use the labelled rate model") from e

    # ---- relay rate, (T, n_cf) in Hz ----
    def relay_rate(self, spec: SoundSpec) -> np.ndarray:
        level = spec.level_db if spec.level_db is not None else self.cfg.periphery.level_db_spl
        key = (spec, level)
        if key not in self._cache:
            T = int(round(spec.dur_s / self.dt))
            if spec.kind == "silence":
                r = np.full((T, self.cf.size), self.cfg.periphery.relay_spont_hz)
            elif self.cfg.periphery.kind == "an":
                r = self._an_relay(render(spec), level, T)
            else:
                r = self._rate_relay(render(spec), level, T)
            self._cache[key] = r
        return self._cache[key]

    def profile(self, spec: SoundSpec) -> np.ndarray:
        """Mean driven relay rate per CF (Hz above spontaneous): the sound's spectral footprint as the
        habituating synapses see it. Used only to SCORE the fingerprint readout, never fed back."""
        return self.relay_rate(spec).mean(axis=0) - self.cfg.periphery.relay_spont_hz

    # ---- kinds ----
    def _map(self, driven: np.ndarray) -> np.ndarray:
        p = self.cfg.periphery
        return p.relay_spont_hz + (p.relay_max_hz - p.relay_spont_hz) * np.clip(driven, 0.0, 1.0)

    def _rate_relay(self, x: np.ndarray, level: float, T: int) -> np.ndarray:
        p = self.cfg.periphery
        x = _level_scale(x, level)
        n_out = T
        cols = []
        for fc in self.cf:
            b, a = signal.gammatone(fc, "iir", fs=FS)
            env = np.abs(signal.hilbert(signal.lfilter(b, a, x)))
            sos = signal.butter(2, 100.0, btype="low", fs=FS, output="sos")
            env = np.clip(signal.sosfiltfilt(sos, env), 0.0, None) / np.sqrt(2)     # ~ running RMS in Pa
            db = 20 * np.log10(np.maximum(env, 1e-12) / P_REF)
            mid = p.rate_threshold_db + p.rate_dynamic_range_db / 2
            drv = 1.0 / (1.0 + np.exp(-(db - mid) / (p.rate_dynamic_range_db / 8)))
            drv[db < p.rate_threshold_db - 10] = 0.0
            cols.append(signal.resample(drv, n_out) if drv.size != n_out else drv)
        return self._map(np.clip(np.array(cols).T, 0.0, 1.0))

    def _an_pooled(self, sound_pa: np.ndarray, T: int, seed: int) -> np.ndarray:
        import cochlea
        p = self.cfg.periphery
        trains = cochlea.run_zilany2014(sound_pa, AN_FS, anf_num=tuple(p.anf_per_cf),
                                        cf=(p.f_lo_hz, p.f_hi_hz, p.n_cf), species="human", seed=seed)
        cfs = np.array(trains["cf"], float)
        spikes = list(trains["spikes"])
        ucf = np.unique(cfs)
        edges = np.arange(T + 1) * self.dt
        out = np.zeros((T, ucf.size))
        for k, cf in enumerate(ucf):
            rows = np.flatnonzero(cfs == cf)
            sp = np.concatenate([np.asarray(spikes[r], float) for r in rows]) if rows.size else np.array([])
            out[:, k] = np.histogram(sp, edges)[0] / (rows.size * self.dt)
        return _smooth(out, self.dt, self.cfg.periphery.smooth_ms)

    def _an_relay(self, x: np.ndarray, level: float, T: int) -> np.ndarray:
        from fractions import Fraction
        import zlib
        fr = Fraction(AN_FS / FS).limit_denominator(1000)
        pa = _level_scale(signal.resample_poly(x, fr.numerator, fr.denominator), level)
        if self._an_spont is None:
            quiet = self._an_pooled(np.zeros(int(1.0 * AN_FS)), int(round(1.0 / self.dt)), seed=7)
            self._an_spont = quiet.mean(axis=0)
        pooled = self._an_pooled(pa, T, seed=zlib.crc32(x.astype(np.float32).tobytes()) % 2**31)   # stable across processes (hash() is not)
        return self._map((pooled - self._an_spont) / self.cfg.periphery.an_driven_ref_hz)


def relay_spikes(rate_cf: np.ndarray, per_cf: int, dt: float, rng: np.random.Generator) -> np.ndarray:
    """(T, n_cf) Hz -> (T, n_cf*per_cf) boolean spikes, independent Poisson per relay unit.
    Relay unit j belongs to CF j // per_cf."""
    r = np.repeat(rate_cf, per_cf, axis=1)
    return rng.random(r.shape) < np.clip(r * dt, 0.0, 1.0)
