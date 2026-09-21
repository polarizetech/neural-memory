"""Turn the input streams into what the core needs: spike trains + metadata, plus decode TARGETS.

The decode targets (per-stream band envelopes, and optionally per-stream auditory-nerve rate
patterns) are computed from each stream ALONE. The network never sees them; they exist only so the
readout can be scored against the truth.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..config import Config
from . import an as anmod
from .base import SpikeInput, StageUnavailable, poisson_spikes
from .brainstem import cn_stage
from .filterbank import Analysis, analyse
from .io import Stream
from .mixing import block_shuffle, projection


@dataclass
class Inputs:
    analyses: list[Analysis]
    env: np.ndarray                 # (S, B, T) TRUE envelopes at env_rate over the encode window
    env_rate: float
    spikes_enc: SpikeInput          # what the core is driven with during encoding
    spikes_cue: SpikeInput | None   # cued stream ALONE, first cue_fraction (recall mode "cue")
    neurophonic: object | None = None       # brainstem.Neurophonic for the ENCODE window (MSO on)
    neurophonic_cue: object | None = None
    an_rate: np.ndarray | None = None      # (S, n_cf, T_dec) per-stream AN rate targets
    an_cf: np.ndarray | None = None
    log: dict = field(default_factory=dict)


def _shuffle_waveform(s: Stream, block_s: float, rng) -> Stream:
    n = int(block_s * s.fs)
    k = s.x.size // n
    order = rng.permutation(k)
    x = s.x.copy()
    for a, b in enumerate(order):
        x[a * n:(a + 1) * n] = s.x[b * n:(b + 1) * n]
    return Stream(s.name, x, s.fs, s.source)


def build_inputs(streams: list[Stream], cfg: Config, keep_fine: bool = False) -> Inputs:
    rng = np.random.default_rng(cfg.seed + 101)
    fe, pr = cfg.frontend, cfg.protocol
    rep = cfg.sim.replicate_offset                      # D3: a different spike-generation stream, same everything else
    ans = [analyse(s, fe, seconds=pr.encode_s, keep_fine=keep_fine) for s in streams]
    T = min(a.env.shape[1] for a in ans)
    env = np.stack([a.env[:, :T] for a in ans])
    S, B, _ = env.shape
    cue_s = pr.cue_fraction * pr.encode_s if pr.cued else 0.0
    shown_streams = ([_shuffle_waveform(s, 0.25, rng) for s in streams] if pr.shuffle_input else streams)
    log: dict = {}

    nph = nph_cue = None
    if fe.kind == "an" and fe.stereo:
        # TWO cochleae. The monaural AN-derived input stays (both nerves); the MSO population is ADDED to it.
        from .brainstem import concat, mso_population
        tonic = cfg.neuromod.tonic

        def binaural(seconds, seed, only=None):
            L, R = anmod.run_an_binaural(anmod.ear_mixtures(shown_streams, seconds, cfg, only=only), cfg, seed + rep, tonic)
            both, n = concat(L, R), None
            if fe.mso:
                m, n = mso_population(L, R, cfg, seed)
                both = concat(both, m)
            both.front_end = "an_stereo+mso" if fe.mso else "an_stereo"
            return both, n
        enc, nph = binaural(pr.encode_s, cfg.seed)
        cue = None
        if cue_s > 0:
            cue, nph_cue = binaural(cue_s, cfg.seed + 1, only=pr.cue_stream)
        log["fibre_axis"] = anmod.fibre_axis(enc)
        log["azimuths_deg"] = [fe.azimuths_deg[k % len(fe.azimuths_deg)] if s.lr is None else "as recorded" for k, s in enumerate(streams)]
    elif fe.mso or fe.stereo:
        raise StageUnavailable("frontend.stereo / frontend.mso need frontend.kind: an")
    elif fe.kind == "an":
        tonic = cfg.neuromod.tonic
        mix = anmod.acoustic_mixture(shown_streams, pr.encode_s, fe.level_db_spl)
        enc = anmod.run_an(mix, cfg, cfg.seed + rep, tonic)
        cue = None
        if cue_s > 0:
            solo = anmod.acoustic_mixture(shown_streams, cue_s, fe.level_db_spl, only=pr.cue_stream)
            cue = anmod.run_an(solo, cfg, cfg.seed + 1 + rep, tonic)
        if fe.brainstem == "cnmodel":
            enc = cn_stage(enc)
        log["fibre_axis"] = anmod.fibre_axis(enc)
    else:
        P = projection(S, B, cfg.mixing, rng)
        shown = np.stack([block_shuffle(e, int(0.25 * fe.envelope_rate_hz), rng) for e in env]) \
            if pr.shuffle_input else env
        dt = 1.0 / fe.envelope_rate_hz
        rates = cfg.mixing.rate_max_hz * np.clip(P @ shown.reshape(S * B, T), 0, 1.5).T
        spk_rng = rng if rep == 0 else np.random.default_rng(cfg.seed + 101 + rep)
        t, i = poisson_spikes(rates, dt, spk_rng)
        meta = dict(population=np.array(["fb"] * P.shape[0], dtype=str),
                    modality=np.array(["generic"] * P.shape[0]))
        enc = SpikeInput(t, i, P.shape[0], T * dt, meta, "filterbank",
                         ["ablation front end: envelope bands -> sparse random projection -> Poisson"])
        cue = None
        if cue_s > 0:
            n_cue = int(round(cue_s / dt))
            cue_env = np.zeros((S, B, n_cue)); cue_env[pr.cue_stream] = shown[pr.cue_stream, :, :n_cue]
            tc, ic = poisson_spikes(cfg.mixing.rate_max_hz * np.clip(P @ cue_env.reshape(S * B, -1), 0, 1.5).T, dt, rng)
            cue = SpikeInput(tc, ic, P.shape[0], cue_s, meta, "filterbank")
        log["projection"] = P

    an_rate = an_cf = None
    if "an_rate" in cfg.decode.targets:
        if fe.kind != "an":
            raise StageUnavailable("decode target 'an_rate' needs frontend.kind: an")
        edges = np.arange(0.0, pr.encode_s + 1e-9, 1.0 / cfg.decode.rate_hz)
        rows = []
        for k in range(S):
            solo = anmod.run_an(anmod.acoustic_mixture(streams, pr.encode_s, fe.level_db_spl, only=k),
                                cfg, cfg.seed + 10 + k, cfg.neuromod.tonic)
            an_cf = np.unique(solo.meta["cf_hz"])
            r = np.array([np.histogram(solo.t[np.isin(solo.i, np.flatnonzero(solo.meta["cf_hz"] == cf))], edges)[0]
                          / ((solo.meta["cf_hz"] == cf).sum() / cfg.decode.rate_hz) for cf in an_cf])
            rows.append(r)
        an_rate = np.stack(rows)
    log["input_rates_hz"] = enc.population_rates()
    log["front_end_notes"] = enc.notes
    return Inputs(ans, env, fe.envelope_rate_hz, enc, cue, nph, nph_cue, an_rate, an_cf, log)
