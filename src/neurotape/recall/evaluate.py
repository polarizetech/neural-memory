"""One run -> one flat dict of metrics. No metric here is ever used to choose a parameter."""
from __future__ import annotations

import numpy as np

from ..config import Config
from ..decode import population as pop
from ..decode import readout as ro


def _features(res, seg_t0, seg_t1, cfg: Config, pool="exc"):
    i, t = res.spikes_e if pool == "exc" else res.spikes_i
    n = res.n_exc if pool == "exc" else res.n_inh
    return ro.activity_features(i, t, n, seg_t0, seg_t1, cfg.decode.rate_hz, cfg.decode.filter_tau_ms)


def stream_identity_from_rank(rank, fired, labels, seed=0, n_perm=200) -> dict:
    """Is the DOMINANT stream of a window recoverable from rank position alone? Nearest-centroid,
    5-fold blocked CV, against a label-permutation null. Same test on the binary fired vector."""
    rng = np.random.default_rng(seed)

    def acc(F, y):
        folds = np.array_split(np.arange(y.size), 5)
        hit = 0
        for f in folds:
            tr = np.setdiff1d(np.arange(y.size), f)
            cls = np.unique(y[tr])
            cen = np.stack([F[tr][y[tr] == c].mean(0) for c in cls])
            d = ((F[f][:, None, :] - cen[None]) ** 2).sum(-1)
            hit += (cls[d.argmin(1)] == y[f]).sum()
        return hit / y.size

    out = {}
    for name, F in (("rank", rank.T.astype(float)), ("fired", fired.T.astype(float))):
        a = acc(F, labels)
        null = np.array([acc(F, rng.permutation(labels)) for _ in range(n_perm)])
        out[name] = dict(acc=float(a), null_mean=float(null.mean()), null_p95=float(np.percentile(null, 95)),
                         p=float((1 + (null >= a).sum()) / (1 + n_perm)))
    return out


def evaluate(res, inputs, cfg: Config, targets: np.ndarray | None = None) -> dict:
    dc = cfg.decode
    S = inputs.env.shape[0]
    Y = ro.resample_targets(inputs.env, inputs.env_rate, dc.rate_hz) if targets is None else targets
    enc = res.timeline.segment("encode")
    X = _features(res, enc.t0, enc.t1, cfg)
    n = min(len(X), len(Y)); X, Y = X[:n], Y[:n]
    ntr = int(dc.train_fraction * n)
    dec = ro.fit_ridge(X[:ntr], Y[:ntr], dc.alphas)
    out: dict = {"alpha": dec.alpha, "n_streams": S}

    pred_te = dec.predict(X[ntr:])
    C = ro.crosstalk(pred_te, Y[ntr:], S)
    out["encode_heldout_r"] = [float(C[k, k]) for k in range(S)]
    out["encode_crosstalk"] = C.tolist()

    # ---- subsets: non-engram cells, rank bands ----
    t_end, rank, fired = ro.rank_table(res, enc)
    eng = ro.engram_cells(res, cfg)
    subsets = {"non_engram": np.flatnonzero(~eng), "engram": np.flatnonzero(eng), **ro.rank_bands(rank)}
    out["n_engram"] = int(eng.sum())
    sub_dec = {}
    for name, units in subsets.items():
        if units.size >= 2:
            sub_dec[name] = ro.fit_ridge(X[:ntr], Y[:ntr], dc.alphas, units=units)
            out[f"encode_heldout_r__{name}"] = float(np.mean(np.diag(ro.crosstalk(sub_dec[name].predict(X[ntr:]), Y[ntr:], S))))

    # ---- rank as a first-class output ----
    out["rank_fired_top10_frac"] = float(fired[rank < max(res.n_exc // 10, 1)].mean())
    out["rank_fired_bottom50_frac"] = float(fired[rank >= res.n_exc // 2].mean())
    if S > 1:
        q = int(round(inputs.env_rate * dc.rank_window_ms * 1e-3))
        e = inputs.env.mean(axis=1)
        e = e / (e.mean(axis=1, keepdims=True) + 1e-12)
        nw = min(e.shape[1] // q, rank.shape[1])
        lab = e[:, :nw * q].reshape(S, nw, q).mean(2).argmax(0)
        if np.unique(lab).size > 1:
            out["stream_identity"] = stream_identity_from_rank(rank[:, :nw], fired[:, :nw], lab, cfg.seed)

    # ---- recall probes: the SAME decoder, unchanged ----
    out["recall"] = []
    # Uncued modes have no time reference: replay, if any, may start anywhere, so the lag search is wide.
    # The null is searched over the SAME range, so the wider search is priced, not free.
    max_lag_s = 1.0 if cfg.protocol.cued else min(0.5 * (cfg.protocol.recall_s or cfg.protocol.encode_s), 5.0)
    si_, st_ = res.spikes_e
    count = lambda a, b: np.bincount(si_[(st_ >= a) & (st_ < b)], minlength=res.n_exc).astype(float)
    enc_counts, settle = count(enc.t0, enc.t1), res.timeline.segment("settle")
    def _pat(a, b):
        c = count(a, b)
        return float(np.corrcoef(c, enc_counts)[0, 1]) if c.std() > 0 and enc_counts.std() > 0 else float("nan")
    out["pattern_r_settle_baseline"] = _pat(settle.t0, settle.t1)
    for seg in res.timeline.recalls():
        Xr = _features(res, seg.t0, seg.t1, cfg)
        m = min(len(Xr), len(Y))
        k0 = int(round(seg.cue_s * dc.rate_hz))                 # exclude the cue itself
        pr, yt = dec.predict(Xr[:m]), Y[:m]
        Cr = ro.crosstalk(pr[k0:], yt[k0:], S)
        k = cfg.protocol.cue_stream
        B = Y.shape[1] // S
        colk = slice(k * B, (k + 1) * B)
        # GUARDED window: starts 1 s after cue offset. Added after the first 10-seed pass returned a
        # recall r of +0.045 that was IDENTICAL at every delay -- the signature of cue carry-over (slow
        # conductances, adaptation and rebound still ringing), not of storage.
        kg = k0 + int(round(1.0 * dc.rate_hz))
        Cg = ro.crosstalk(pr[kg:], yt[kg:], S) if m - kg > 50 else np.full((S, S), np.nan)
        bl = ro.bestlag_with_null(pr[kg:, colk], yt[kg:, colk], dc.rate_hz, max_lag_s, dc.n_surrogates, cfg.seed)
        rec = dict(delay_s=seg.delay_s, delay_bio_s=seg.delay_s * cfg.time_compression,
                   # RATE-PATTERN reactivation: do the cells that fired during encoding fire during recall?
                   # (per-cell spike counts, guarded window) -- the question an STC assembly can answer.
                   pattern_r=_pat(seg.t0 + seg.cue_s + 1.0, seg.t1), n_spikes=int(count(seg.t0 + seg.cue_s + 1.0, seg.t1).sum()),
                   guarded_r=[float(Cg[j, j]) for j in range(S)],
                   locked_r=[float(Cr[j, j]) for j in range(S)], crosstalk=Cr.tolist(),
                   bestlag=bl, ordering_rho=ro.ordering_score(pr[kg:, colk], yt[:, colk], dc.rate_hz),
                   rate_e_hz=float(((res.spikes_e[1] >= seg.t0 + seg.cue_s) & (res.spikes_e[1] < seg.t1)).sum()
                                   / res.n_exc / max(seg.dur - seg.cue_s, 1e-9)))
        for name, d in sub_dec.items():
            rec[f"locked_r__{name}"] = float(np.mean(np.diag(ro.crosstalk(d.predict(Xr[:m])[k0:], yt[k0:], S))))
        out["recall"].append(rec)

    # ---- population signal: LFP proxy, TRF, theta locking per stream ----
    sel = (res.lfp_t >= enc.t0) & (res.lfp_t < enc.t1)
    lfp = pop.lfp_proxy(res.lfp_Ie[sel], res.lfp_Ii[sel], Irec_pA=res.lfp_Ir[sel])["rws_recurrent"]
    env1k = inputs.env.mean(axis=1)
    m = min(lfp.size, env1k.shape[1])
    lags, w, r = pop.fit_trf(env1k.mean(0)[:m], lfp[:m], inputs.env_rate)
    out["trf"] = dict(r_heldout=r, peak_lag_ms=float(lags[np.argmax(np.abs(w))] * 1e3))
    out["theta_locking"] = pop.theta_locking(lfp[:m], env1k[:, :m], inputs.env_rate, cfg.theta.f_hz)

    # ---- bookkeeping the report needs ----
    st = res.state_e[:, (res.state_t >= enc.t0) & (res.state_t < enc.t1)]
    out["state_frac_encode"] = (np.bincount(st.ravel().astype(int), minlength=4) / max(st.size, 1)).tolist()
    out["h_final_mean"] = float(res.h_final.mean()); out["z_final_max"] = float(res.z_final.max())
    out["frac_late"] = float((np.abs(res.z_final) > 0.05).mean())
    out["p_max"] = float(res.p.max()); out["creb_max"] = float(res.creb.max())
    out["nm_events"] = int(len(res.nm.events_s)); out["wall_s"] = float(res.wall_s)
    i, t = res.spikes_e
    cons = [sg for sg in res.timeline.segments if sg.kind == "consolidate"]
    out["rate_e_consolidate_hz"] = float(sum(((t >= sg.t0) & (t < sg.t1)).sum() for sg in cons) / res.n_exc / max(sum(sg.dur for sg in cons), 1e-9))
    out["rate_e_encode_hz"] = float(((t >= enc.t0) & (t < enc.t1)).sum() / res.n_exc / enc.dur)
    return out, dec
