"""Global LC-like neuromodulator: NM(t) = tonic level (may ramp) + phasic transients.

Phasic transients are triggered by SALIENCE, defined as the mismatch between the input envelope
and its own running average. Salience depends only on the input, so the whole NM(t) trace is
computed before the simulation and handed to Brian2 as a TimedArray.

NM scales three things (network.py / neurons/model.py):
  * input gain:                 gain = 1 + k_gain * (NM - nm_ref)
  * protein-synthesis threshold: theta_pro = h_0 / (NM + 0.001)     [Lehr et al. 2022]
  * inhibitory set point:       bias current to I cells = k_inh * (NM - nm_ref)

The tonic/phasic split follows the adaptive-gain account of locus coeruleus function
(Aston-Jones & Cohen 2005, Annu Rev Neurosci 28:403 -- cited from memory). The specific kernel,
threshold and gains are phenomenological placeholders: see ASSUMPTIONS.md.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..config import Config

NM_DT_S = 0.01


@dataclass
class NMTrace:
    t: np.ndarray            # seconds, NM_DT_S grid over the whole timeline
    nm: np.ndarray
    tonic: np.ndarray
    events_s: np.ndarray     # phasic event onsets
    salience: np.ndarray


def salience(env_mean: np.ndarray, rate_hz: float, tau_s: float) -> np.ndarray:
    """|x - running_average(x)| with a causal exponential running average."""
    a = 1.0 / max(tau_s * rate_hz, 1.0)
    avg = np.empty_like(env_mean)
    m = env_mean[0]
    for k, v in enumerate(env_mean):
        m += a * (v - m)
        avg[k] = m
    return np.abs(env_mean - avg)


def build_nm(cfg: Config, timeline, env: np.ndarray, env_rate: float) -> NMTrace:
    """``timeline`` is a recall.protocol.Timeline; ``env`` is (S, B, T), the per-stream envelopes
    over the encode window. Salience uses their grand mean (what the mixture delivers)."""
    nmc = cfg.neuromod
    env_mean_encode = env.mean(axis=(0, 1))
    t = np.arange(0.0, timeline.total_s + NM_DT_S, NM_DT_S)
    tonic = np.full_like(t, nmc.tonic)
    enc = timeline.segment("encode")
    if nmc.tonic_ramp_to is not None:
        sel = (t >= enc.t0) & (t < enc.t1)
        tonic[sel] = np.linspace(nmc.tonic, nmc.tonic_ramp_to, sel.sum())
        tonic[t >= enc.t1] = nmc.tonic_ramp_to
    for seg in timeline.segments:
        if seg.kind == "consolidate":
            tonic[(t >= seg.t0) & (t < seg.t1)] = nmc.consolidation_tonic

    sal = salience(env_mean_encode, env_rate, nmc.salience_tau_s)
    events: list[float] = []
    nm = tonic.copy()
    if cfg.mechanisms.nm_dynamic:
        z = (sal - sal.mean()) / (sal.std() + 1e-12)
        last = -np.inf
        for k in np.flatnonzero(z > nmc.salience_z):
            tk = k / env_rate
            if tk - last >= nmc.salience_refractory_s:
                events.append(enc.t0 + tk)
                last = tk
        for te in events:                      # alpha-function transient, peak = phasic_amp
            s = np.clip(t - te, 0.0, None) / nmc.phasic_tau_s
            nm += nmc.phasic_amp * s * np.exp(1.0 - s) * (t >= te)
        att = cfg.attention
        if att.stream is not None:
            # attention as NM gain: NM follows the ATTENDED stream's (smoothed) envelope
            e = env[att.stream].mean(axis=0)
            k = max(int(0.1 * env_rate), 1)
            e = np.convolve(e, np.ones(k) / k, mode="same")
            e = e / (np.percentile(e, 99) + 1e-12)
            nm += att.amp * np.interp(t - enc.t0, np.arange(e.size) / env_rate, e, left=0.0, right=0.0)
        if cfg.protocol.recall_mode == "nm_pulse":
            for seg in timeline.segments:
                if seg.kind == "recall":
                    nm[(t >= seg.t0) & (t < seg.t0 + nmc.pulse_s)] += nmc.pulse_amp
    else:
        # flat-NM ablation: constant at the tonic level, no ramp, no phasic, no pulse
        nm = np.full_like(t, nmc.tonic)
        tonic = nm.copy()
    nm = np.clip(nm, 0.0, nmc.nm_max)
    return NMTrace(t, nm, tonic, np.array(events), sal)
