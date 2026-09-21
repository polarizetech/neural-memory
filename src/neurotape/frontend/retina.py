"""Video front end -- LATER MILESTONE. Interface only; audio is implemented end-to-end first.

A retina front end returns the same thing every front end returns: a ``SpikeInput`` whose metadata
carries ``population`` in {"on", "off"}, ``modality`` = "video" and a pixel/RF coordinate per unit.
Candidate simulators, neither installed nor evaluated here:
  * Macaque Retina Simulator (Vanni lab; Python, parasol/midget ON/OFF units)
  * RetinoSim (event-camera-style retina-inspired simulator)
The event-camera comparison named in the evaluation plan (experiments/codec.py) is likewise
not built for video; it reports ``unavailable`` rather than a number.
"""
from __future__ import annotations

from .base import SpikeInput, StageUnavailable

BACKENDS = ("macaque_retina_simulator", "retinosim")


def encode_video(path, backend: str = "macaque_retina_simulator", **kw) -> SpikeInput:
    if backend not in BACKENDS:
        raise ValueError(f"unknown retina backend {backend!r}; known: {BACKENDS}")
    raise StageUnavailable(f"retina front end ({backend}) is a later milestone: the core accepts its "
                           "SpikeInput already, but no backend is wired or installed")
