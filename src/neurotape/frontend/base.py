"""The core is modality-agnostic: a front end hands it SPIKE TRAINS PLUS METADATA, nothing else.

Front ends
  an          auditory nerve, Zilany, Bruce & Carney 2014 via the `cochlea` package (PRIMARY, audio)
  filterbank  gammatone/log band-pass envelopes -> sparse random projection -> Poisson (ABLATION,
              and the only route for non-audio CSV sensor streams)
  retina      ON/OFF spike populations from a retina simulator (LATER MILESTONE: interface only)

Optional stages layered on ``an``: a brainstem stage (cnmodel bushy/stellate) and an MSO
coincidence stage for stereo input -- see brainstem.py. Optional efferent (MOC-like) feedback:
tonic NM scales cochlear gain -- applied in an.py before the cochlea runs.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


class StageUnavailable(RuntimeError):
    """Raised instead of silently substituting another stage. A run that quietly fell back from an
    auditory-nerve front end to a filterbank would be reported as something it was not."""


@dataclass
class SpikeInput:
    t: np.ndarray                 # spike times, seconds from the start of the stimulus
    i: np.ndarray                 # unit index per spike
    n: int                        # number of units
    duration: float
    meta: dict = field(default_factory=dict)   # per-unit arrays: population, cf_hz, modality, axis
    front_end: str = ""
    notes: list[str] = field(default_factory=list)

    def window(self, t0: float, t1: float) -> "SpikeInput":
        sel = (self.t >= t0) & (self.t < t1)
        return SpikeInput(self.t[sel] - t0, self.i[sel], self.n, t1 - t0, self.meta,
                          self.front_end, self.notes)

    def mean_rate(self) -> float:
        return self.t.size / max(self.n * self.duration, 1e-12)

    def population_rates(self) -> dict[str, float]:
        pops = np.asarray(self.meta.get("population", np.array(["all"] * self.n)))
        out = {}
        for p in np.unique(pops):
            units = np.flatnonzero(pops == p)
            out[str(p)] = float(np.isin(self.i, units).sum() / max(units.size * self.duration, 1e-12))
        return out


def poisson_spikes(rates_hz: np.ndarray, dt: float, rng: np.random.Generator):
    """rates_hz: (T, n). Returns (t, i) with at most one spike per bin."""
    hit = rng.random(rates_hz.shape) < np.clip(rates_hz * dt, 0.0, 1.0)
    k, i = np.nonzero(hit)
    t = (k + rng.random(k.size)) * dt
    order = np.argsort(t, kind="stable")
    return t[order], i[order]
