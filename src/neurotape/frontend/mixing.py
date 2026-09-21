"""Fixed sparse random projection from (stream, band) envelopes onto input neurons.

In ``mixed`` mode every input neuron draws its bands from ALL streams, so nothing upstream of the
network tells it which stream a given input belongs to. ``labelled`` is a debug mode: each input
neuron prefers one stream with probability ``label_purity``.
"""
from __future__ import annotations

import numpy as np

from ..config import Mixing


def projection(n_streams: int, n_bands: int, cfg: Mixing, rng: np.random.Generator) -> np.ndarray:
    """(n_input, n_streams * n_bands) non-negative, rows sum to 1."""
    n_feat = n_streams * n_bands
    k = min(cfg.bands_per_input, n_feat)
    P = np.zeros((cfg.n_input, n_feat))
    for i in range(cfg.n_input):
        if cfg.mode == "labelled":
            home = i % n_streams
            idx = []
            for _ in range(k):
                s = home if rng.random() < cfg.label_purity else rng.integers(n_streams)
                idx.append(s * n_bands + rng.integers(n_bands))
            idx = np.array(idx)
        else:
            idx = rng.choice(n_feat, size=k, replace=False)
        np.add.at(P[i], idx, rng.uniform(0.5, 1.0, size=idx.size))
        P[i] /= P[i].sum()
    return P


def stream_purity(P: np.ndarray, n_streams: int) -> np.ndarray:
    """Per input neuron: largest share of its weight coming from a single stream."""
    n_bands = P.shape[1] // n_streams
    shares = P.reshape(P.shape[0], n_streams, n_bands).sum(axis=2)
    return shares.max(axis=1)


def block_shuffle(env: np.ndarray, block: int, rng: np.random.Generator) -> np.ndarray:
    """Shuffled-input control: permute time blocks, identically across bands of one stream."""
    T = env.shape[-1]
    n = T // block
    order = rng.permutation(n)
    out = env.copy()
    for k, j in enumerate(order):
        out[..., k * block:(k + 1) * block] = env[..., j * block:(j + 1) * block]
    return out
