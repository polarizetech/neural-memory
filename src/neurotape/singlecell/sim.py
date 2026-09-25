"""Run a stimulus protocol on one simulated Stentor cell and record what happens.

A protocol is a list of Stim events (time in minutes, channel, force, kind). kind "stim" is a real stimulus
(response evaluated, then receptors internalised or modified); kind "probe" is the authors' virtual test stimulus
(response evaluated, nothing internalised). Between events libRoadRunner integrates the Antimony model exactly.

Outputs
  events  one row per event: time, channel, force, kind, P_act, lambda (mean open channels), p_response,
          expected membrane depolarisation (voltage divider on the mean open count), and the pools just before
  trace   dense samples of every pool at `sample_dt` minutes, for plots and the animation
  The model is deterministic (it returns the PROBABILITY of contraction, as the authors' deterministic model does).
  `sample_responses` draws one cell's contract / no-contract sequence from those probabilities, seeded, for display.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.stats import poisson

from .models import CellConfig, antimony


@dataclass(frozen=True)
class Stim:
    t: float                    # minutes
    channel: int = 0
    force: float = 2.0
    kind: str = "stim"          # "stim" | "probe"


def train(t0: float, force: float, period: float, n: int, channel: int = 0, kind: str = "stim") -> list[Stim]:
    """n stimuli, the first at t0 + period (the authors' convention: each triple adds `period` before a stimulus)."""
    return [Stim(t0 + period * (k + 1), channel, force, kind) for k in range(n)]


def sequence(triples: list[tuple], channel: int = 0, t0: float = 0.0) -> list[Stim]:
    """The authors' stimulus_sequence_list: (force, period, count); force 0 = probe at `probe_force` (see run)."""
    out, t = [], t0
    for force, period, n in triples:
        for _ in range(int(n)):
            t += period
            out.append(Stim(t, channel, force, "stim" if force > 0 else "probe"))
    return out


def p_act(cfg: CellConfig, force: float) -> float:
    p = cfg.params
    return p.io_max / (1.0 + math.exp(-p.scale * (force - p.F_mid)))


def response_probability(cfg: CellConfig, lam: float) -> float:
    """P(number open > n_min), Poisson(lam) -- the authors' 1 - cdf('Poisson', n_min, lam)."""
    return float(1.0 - poisson.cdf(cfg.params.n_min, lam)) if lam > 0 else 0.0


def depolarisation(cfg: CellConfig, n_open: float) -> float:
    """Receptor potential from the authors' voltage divider, V = V_i n / (S_a + n S_b) -- the form their threshold
    n_min = (V_th/V_i) S_a / (1 - (V_th/V_i) S_b) solves for. Contraction needs V > V_th (0.012)."""
    p = cfg.params
    return p.V_i * n_open / (p.S_a + n_open * p.S_b) if n_open > 0 else 0.0


def run(cfg: CellConfig, protocol: list[Stim], t_end: float | None = None, sample_dt: float = 0.25,
        probe_force: float | None = None) -> dict:
    import tellurium as te
    rr = te.loada(antimony(cfg))
    C = cfg.n_channels
    ev = sorted(protocol, key=lambda s: s.t)
    t_end = max(t_end or 0.0, ev[-1].t if ev else 0.0)
    t = 0.0
    trace = {"t": [0.0], **{f"S{c}": [rr[f"S{c}"]] for c in range(C)}, **{f"I{c}": [rr[f"I{c}"]] for c in range(C)}}
    has_x = cfg.recycling == "labile"
    if has_x:
        trace["X"] = [rr["X"]]
    rows = []
    blocked = False

    def advance(to: float):
        nonlocal t, blocked
        while t < to - 1e-12:
            nxt = to
            if not blocked and cfg.synthesis_scale != 1.0 and t < cfg.block_from_min < to:
                nxt = cfg.block_from_min
            n = max(int(math.ceil((nxt - t) / sample_dt)), 1)
            res = rr.simulate(t, nxt, n + 1)
            cols = res.colnames
            for row in np.asarray(res)[1:]:
                trace["t"].append(float(row[0]))
                for c in range(C):
                    trace[f"S{c}"].append(float(row[cols.index(f"[S{c}]")]))
                    trace[f"I{c}"].append(float(row[cols.index(f"[I{c}]")]))
                if has_x:
                    trace["X"].append(float(row[cols.index("[X]")]))
            t = nxt
            if not blocked and cfg.synthesis_scale != 1.0 and t >= cfg.block_from_min - 1e-12:
                rr["syn"] = cfg.synthesis_scale
                blocked = True

    if cfg.synthesis_scale != 1.0 and cfg.block_from_min <= 0.0:
        rr["syn"] = cfg.synthesis_scale
        blocked = True
    for s in ev:
        advance(s.t)
        c = s.channel
        S_before = float(rr[f"S{c}"])
        force = s.force if s.kind == "stim" else (probe_force if probe_force is not None else s.force)
        pa = p_act(cfg, force)
        lam = pa * S_before
        pr = response_probability(cfg, lam)
        rows.append(dict(t=s.t, channel=c, force=force, kind=s.kind, P_act=pa, lam=lam, p_response=pr,
                         V=depolarisation(cfg, lam), S_before=S_before, I_before=float(rr[f"I{c}"]),
                         S_all=[float(rr[f"S{k}"]) for k in range(C)], I_all=[float(rr[f"I{k}"]) for k in range(C)]))
        if s.kind == "stim":
            moved = cfg.params.k_int * pa * S_before
            rr[f"S{c}"] = S_before - moved
            rr[f"I{c}"] = float(rr[f"I{c}"]) + moved
            trace["t"].append(s.t)
            for k in range(C):
                trace[f"S{k}"].append(float(rr[f"S{k}"]))
                trace[f"I{k}"].append(float(rr[f"I{k}"]))
            if has_x:
                trace["X"].append(float(rr["X"]))
    advance(t_end)
    return dict(config=cfg.to_dict(), events=rows, trace=trace)


def sample_responses(result: dict, seed: int) -> list[int]:
    """One cell's contract (1) / no-contract (0) sequence, drawn from the deterministic probabilities."""
    rng = np.random.default_rng(seed)
    return [int(rng.random() < r["p_response"]) for r in result["events"]]
