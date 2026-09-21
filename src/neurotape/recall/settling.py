"""C8 -- per-cycle analysis of iterative settling, and the completion metric of C7. ANALYSIS ONLY.

Nothing here feeds back into a simulation: stream labels, assembly identity and decoder output are used
to SCORE a run, never to steer it."""
from __future__ import annotations

import numpy as np

from ..decode import readout as ro
from .provenance import reconstructed_fraction


def non_cue_cells(res, view: np.ndarray | None) -> dict:
    """E cells the cue did NOT drive. STRICT = no input synapse from any cued channel. At this network's input
    connectivity (each E cell receives ~10% of the channels) the strict set is usually EMPTY, so the
    least-driven quartile is returned beside it -- labelled, and weaker: those cells are still cue-driven."""
    i, j = res.extra["in_e"]; n = res.n_exc
    if view is None:
        view = np.unique(i)
    counts = np.bincount(j[np.isin(i, view)], minlength=n)
    strict = np.flatnonzero(counts == 0)
    return dict(strict=strict, least_driven_quartile=np.argsort(counts, kind="stable")[:max(n // 4, 2)], cue_inputs_per_cell=counts)


def per_cycle(res, inputs, cfg, dec, Y, foreign, seg, units=None) -> list[dict]:
    """One row per settling cycle: firing rate, overlap with the encoding assembly, decoded own-vs-foreign
    score, reconstructed fraction. `units` restricts the DECODER to a cell subset (the completion metric)."""
    dc = cfg.decode; i, t = res.spikes_e; enc = res.timeline.segment("encode")
    enc_counts = np.bincount(i[(t >= enc.t0) & (t < enc.t1)], minlength=res.n_exc).astype(float)
    k_ = cfg.protocol.cue_stream; B = inputs.env.shape[1]; col = slice(k_ * B, (k_ + 1) * B)
    period = seg.period_s if seg.period_s > 0 else seg.dur
    rows = []
    for c, onset in enumerate(seg.cue_onsets):
        a, b = seg.t0 + onset, min(seg.t0 + onset + period, seg.t1)
        sel = (t >= a) & (t < b); counts = np.bincount(i[sel], minlength=res.n_exc).astype(float)
        X = ro.activity_features(i, t, res.n_exc, a, b, dc.rate_hz, dc.filter_tau_ms)
        m = min(len(X), len(Y)); pr = dec.predict(X[:m])[:, col]; lag = int(0.5 * dc.rate_hz)
        own = float(np.nanmax(ro._lagged(pr, Y[:m, col], lag))) if np.isfinite(pr).all() and pr.std() > 0 else float("nan")
        oth = np.array([np.nanmax(ro._lagged(pr, F[:m], lag)) for F in foreign]) if np.isfinite(own) else np.array([np.nan])
        rows.append(dict(cycle=c, rate_hz=float(sel.sum() / res.n_exc / max(b - a, 1e-9)), active_fraction=float((counts > 0).mean()),
                         overlap_r=float(np.corrcoef(counts, enc_counts)[0, 1]) if counts.std() > 0 and enc_counts.std() > 0 else float("nan"),
                         own=own, foreign_mean=float(np.nanmean(oth)), foreign_max=float(np.nanmax(oth)),
                         foreign_p=float((1 + np.nansum(oth >= own)) / (1 + len(oth))) if np.isfinite(own) else 1.0,
                         **{k: v for k, v in reconstructed_fraction(res, a, b).items() if k != "available"}))
    return rows


def classify(rows: list[dict], runaway_hz: float = 20.0) -> str:
    """converging   the own-stream margin grows over cycles and ends above every foreign stream
    confabulating the network settles, over cycles, onto a FOREIGN stream -- reported as such, not as failure
    runaway      firing grows without bound (rate multiplies and ends above `runaway_hz`)
    flat         none of the above (including a single cycle, and silence)"""
    if len(rows) < 2:
        return "flat"
    rate = np.array([r["rate_hz"] for r in rows]); margin = np.array([r["own"] - r["foreign_max"] for r in rows])
    if rate[-1] > runaway_hz and rate[-1] > 3.0 * max(rate[0], 1e-9):
        return "runaway"
    if not np.isfinite(margin).all():
        return "flat"
    slope = np.polyfit(np.arange(len(margin)), margin, 1)[0]
    if margin[-1] > 0 and slope > 0:
        return "converging"
    if margin[-1] < 0 and slope < 0:
        return "confabulating"
    return "flat"
