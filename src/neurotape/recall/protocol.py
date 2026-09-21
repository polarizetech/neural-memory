"""The timeline: settle -> encode -> [consolidate -> recall probe] x K.

One simulation covers the whole timeline, so a recall probe reads the SAME network that encoded,
after the stated delay. Caveat, printed in the report: with several probes on one timeline, an
earlier probe is itself an experience and can alter what a later probe finds. Give a single delay
to get an uncontaminated probe.

Recall modes
  cue       the first ``cue_fraction`` of ONE stream is replayed (other streams silent), then nothing
  no_cue    background noise only: spontaneous replay, if any
  nm_pulse  background noise plus a neuromodulator pulse at probe onset, no input
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..config import Config


@dataclass
class Segment:
    name: str
    kind: str                 # settle | encode | consolidate | recall
    t0: float
    t1: float
    delay_s: float | None = None     # recall only: simulated seconds since encoding ended
    cue_s: float = 0.0
    cue_onsets: tuple = (0.0,)       # C8: cue onsets relative to t0, one per settling cycle (K = 1 -> just 0)
    period_s: float = 0.0

    @property
    def dur(self) -> float:
        return self.t1 - self.t0


@dataclass
class Timeline:
    segments: list[Segment] = field(default_factory=list)

    @property
    def total_s(self) -> float:
        return self.segments[-1].t1

    def segment(self, name: str) -> Segment:
        return next(s for s in self.segments if s.name == name)

    def recalls(self) -> list[Segment]:
        return [s for s in self.segments if s.kind == "recall"]


def build_timeline(cfg: Config) -> Timeline:
    p = cfg.protocol
    rec = p.recall_s if p.recall_s is not None else p.encode_s
    cue = p.cue_fraction * p.encode_s if p.cued else 0.0
    K = cfg.settling.k_cycles if cfg.settling_active else 1
    period = cue + cfg.settling.cycle_gap_s
    if K > 1:
        rec = max(rec, K * period)
    onsets = tuple(c * period for c in range(K))
    segs = [Segment("settle", "settle", 0.0, p.settle_s)]
    t = p.settle_s
    segs.append(Segment("encode", "encode", t, t + p.encode_s))
    t += p.encode_s
    consolidated = 0.0
    for k, d in enumerate(sorted(p.recall_delays_s)):
        gap = d - consolidated
        if gap > 0:
            segs.append(Segment(f"consolidate{k}", "consolidate", t, t + gap))
            t += gap
            consolidated = d
        segs.append(Segment(f"recall{k}", "recall", t, t + rec, delay_s=d, cue_s=cue, cue_onsets=onsets, period_s=period))
        t += rec
    return Timeline(segs)
