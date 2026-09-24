"""Ridge readout, trained ONLY on encode-phase activity and applied UNCHANGED to recall activity.

Everything this module returns is a RECONSTRUCTION -- a linear map from network activity to
per-stream band envelopes -- and is labelled so wherever it is written out.

Scores
  encode_heldout  r on the last (1 - train_fraction) of encoding: can the code be read at all
  recall_locked   r between decoded recall and the true stream, time-locked to recall onset
                  (cue mode: over the post-cue continuation only -- the cue itself is excluded)
  recall_bestlag  max over lag of the same, WITH a null: the identical statistic against IAAFT
                  surrogates of the true envelopes (uwtl.surrogates.iaaft). Envelopes are
                  non-negative and skewed, so plain phase randomisation is the wrong null here
                  (tools/REGISTRY.md, "uwtl.surrogates -- AAFT/IAAFT").
  ordering        Spearman rho between recall time and the best-matching stimulus time per chunk:
                  is what comes back in the ORDER it went in
  smear_ms        FWHM of the decoded-vs-true cross-correlation peak: temporal smearing
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

from ..config import Config


def activity_features(spike_i, spike_t, n_units, t0, t1, rate_hz, tau_ms) -> np.ndarray:
    """(T, n_units) causally exp-filtered spike counts on the decode grid."""
    nT = int(round((t1 - t0) * rate_hz))
    sel = (spike_t >= t0) & (spike_t < t0 + nT / rate_hz)
    k = np.minimum(((spike_t[sel] - t0) * rate_hz).astype(int), nT - 1)
    X = np.zeros((nT, n_units))
    np.add.at(X, (k, spike_i[sel]), 1.0)
    a = np.exp(-1.0 / (tau_ms * 1e-3 * rate_hz))
    for j in range(1, nT):
        X[j] += a * X[j - 1]
    return X


def resample_targets(env: np.ndarray, env_rate: float, rate_hz: float) -> np.ndarray:
    """(S, B, T) at env_rate -> (T_dec, S*B) by block averaging."""
    S, B, T = env.shape
    q = int(round(env_rate / rate_hz))
    n = T // q
    return env[:, :, :n * q].reshape(S, B, n, q).mean(axis=3).reshape(S * B, n).T


@dataclass
class Ridge:
    W: np.ndarray
    mu: np.ndarray
    sd: np.ndarray
    ymu: np.ndarray
    alpha: float
    units: np.ndarray

    def predict(self, X: np.ndarray) -> np.ndarray:
        return ((X[:, self.units] - self.mu) / self.sd) @ self.W + self.ymu


def fit_ridge(X, Y, alphas, units=None, n_folds: int = 5) -> Ridge:
    units = np.arange(X.shape[1]) if units is None else np.asarray(units)
    Xu = X[:, units]
    mu, sd = Xu.mean(0), Xu.std(0) + 1e-9
    Z, ymu = (Xu - mu) / sd, Y.mean(0)
    Yc = Y - ymu
    U, s, Vt = np.linalg.svd(Z, full_matrices=False)
    folds = np.array_split(np.arange(Z.shape[0]), n_folds)          # blocked CV, inside ENCODE only
    best, best_a = -np.inf, alphas[0]
    for a in alphas:
        sc = []
        for f in folds:
            tr = np.setdiff1d(np.arange(Z.shape[0]), f)
            Uf, sf, Vf = np.linalg.svd(Z[tr], full_matrices=False)
            Wf = Vf.T @ ((sf / (sf ** 2 + a))[:, None] * (Uf.T @ Yc[tr]))
            sc.append(mean_corr(Z[f] @ Wf, Yc[f]))
        if np.nanmean(sc) > best:
            best, best_a = np.nanmean(sc), a
    W = Vt.T @ ((s / (s ** 2 + best_a))[:, None] * (U.T @ Yc))
    return Ridge(W, mu, sd, ymu, float(best_a), units)


def mean_corr(A: np.ndarray, B: np.ndarray) -> float:
    """Mean over columns of Pearson r; columns with no variance are skipped."""
    a, b = A - A.mean(0), B - B.mean(0)
    den = np.sqrt((a ** 2).sum(0) * (b ** 2).sum(0))
    ok = den > 1e-12
    return float(np.mean((a * b).sum(0)[ok] / den[ok])) if ok.any() else float("nan")


def crosstalk(pred: np.ndarray, true: np.ndarray, S: int) -> np.ndarray:
    """C[i, j] = mean over bands of r(decoded stream i, true stream j). Diagonal = fidelity."""
    B = pred.shape[1] // S
    C = np.zeros((S, S))
    for i in range(S):
        for j in range(S):
            C[i, j] = mean_corr(pred[:, i * B:(i + 1) * B], true[:, j * B:(j + 1) * B])
    return C


def _lagged(pred, true, max_lag):
    out = []
    for L in range(-max_lag, max_lag + 1):
        if L >= 0:
            a, b = pred[L:], true[:true.shape[0] - L]
        else:
            a, b = pred[:L], true[-L:]
        n = min(len(a), len(b))
        out.append(mean_corr(a[:n], b[:n]) if n > 10 else np.nan)
    return np.array(out)


def bestlag_with_null(pred, true, rate_hz, max_lag_s, n_surr, seed) -> dict:
    from ..monorepo import import_uwtl
    import_uwtl()
    from uwtl.surrogates import iaaft
    max_lag = int(max_lag_s * rate_hz)
    cc = _lagged(pred, true, max_lag)
    if not np.isfinite(cc).any():
        # a recall window with NO spikes decodes to a constant: every correlation is undefined. That is a
        # legitimate outcome (total silence), not an error -- it crashed one of 180 drive runs before this guard.
        return dict(r=float("nan"), lag_ms=float("nan"), null_mean=float("nan"), null_p95=float("nan"), p=1.0,
                    null_shift_p95=float("nan"), p_iaaft=1.0, smear_ms=float("nan"), silent=True)
    obs = float(np.nanmax(cc))
    rng = np.random.default_rng(seed)
    null = []
    # IAAFT is the SECONDARY null and costs ~20 ms per band per surrogate in pure numpy: at 100
    # surrogates x 32 bands x 3 probes it was 3+ minutes of every job (measured by sampling a worker).
    # It runs on at most 20 surrogates and 8 evenly spaced bands; the primary shift null uses n_surr.
    cols = np.unique(np.linspace(0, true.shape[1] - 1, min(8, true.shape[1])).astype(int))
    for _ in range(min(n_surr, 20)):
        surr = true.copy()
        for c in cols:
            if true[:, c].std() > 1e-9:
                surr[:, c] = iaaft(true[:, c], rng=rng, n_iter=30)
        surr = surr[:, cols]; pred_c = pred[:, cols]
        null.append(np.nanmax(_lagged(pred_c, surr, max_lag)))
    null = np.array(null)
    # PRIMARY null: circular time shifts of the TRUE envelopes (uwtl ladder S1). It keeps the
    # cross-band co-modulation that per-band IAAFT destroys -- with IAAFT alone a near-silent network
    # "recalled" at p = 0.02, because any blip correlates with ALL bands of a real envelope at once.
    T = true.shape[0]
    lo = min(2 * max_lag + 1, T // 3)
    shifts = rng.integers(lo, max(T - lo, lo + 1), size=n_surr)
    null_shift = np.array([np.nanmax(_lagged(pred, np.roll(true, int(s), axis=0), max_lag)) for s in shifts])
    lags_ms = np.arange(-max_lag, max_lag + 1) / rate_hz * 1e3
    half = cc >= (np.nanmax(cc) + np.nanmedian(cc)) / 2.0
    return dict(r=obs, lag_ms=float(lags_ms[int(np.nanargmax(cc))]),
                null_mean=float(null.mean()), null_p95=float(np.percentile(null, 95)),
                p=float((1 + (null_shift >= obs).sum()) / (1 + n_surr)),
                null_shift_p95=float(np.percentile(null_shift, 95)),
                p_iaaft=float((1 + (null >= float(np.nanmax(_lagged(pred[:, cols], true[:, cols], max_lag)))).sum()) / (1 + len(null))),
                smear_ms=float(half.sum() / rate_hz * 1e3))


def ordering_score(pred, true, rate_hz, chunk_s=0.5) -> float:
    """Spearman rho between chunk position in recall and the stimulus time it best matches."""
    n = int(chunk_s * rate_hz)
    k = pred.shape[0] // n
    if k < 4:
        return float("nan")
    where = []
    for c in range(k):
        seg = pred[c * n:(c + 1) * n]
        best = [mean_corr(seg, true[j:j + n]) for j in range(0, true.shape[0] - n + 1, max(n // 2, 1))]
        where.append(int(np.nanargmax(best)) if np.isfinite(best).any() else 0)
    return float(stats.spearmanr(np.arange(k), where)[0])


def engram_cells(res, cfg: Config) -> np.ndarray:
    """Boolean per E cell. 'protein': the protein pool ever crossed threshold (the per-neuron STC
    allocation event). 'late_weight': mean incoming late weight z at the end crossed it."""
    if cfg.decode.engram_metric == "protein":
        return res.p.max(axis=1) >= cfg.decode.engram_threshold
    zsum = np.bincount(res.syn_j, weights=res.z_final, minlength=res.n_exc)
    cnt = np.maximum(np.bincount(res.syn_j, minlength=res.n_exc), 1)
    return zsum / cnt >= cfg.decode.engram_threshold


def rank_table(res, seg) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per rank window inside ``seg``: (window_end_times, rank (n_exc, n_win; 0 = highest drive),
    fired (n_exc, n_win) bool). Rank is a first-class output, not a win/lose bit."""
    w = res.cfg.decode.rank_window_ms * 1e-3
    sel = (res.rank_t > seg.t0 + 1e-9) & (res.rank_t <= seg.t1 + 1e-9)
    t_end, drive = res.rank_t[sel], res.drive[:, sel]
    rank = np.argsort(np.argsort(-drive, axis=0), axis=0)
    i, t = res.spikes_e
    fired = np.zeros_like(drive, dtype=bool)
    k = np.searchsorted(t_end, t, side="left")
    ok = (k < t_end.size) & (t > t_end[np.clip(k, 0, t_end.size - 1)] - w)
    fired[i[ok], k[ok]] = True
    return t_end, rank, fired


def rank_bands(rank: np.ndarray) -> dict[str, np.ndarray]:
    """Cells grouped by MEAN rank during encoding: top 10%, 10-50%, bottom 50%."""
    order = np.argsort(rank.mean(axis=1))
    n = order.size
    return {"top10": order[:max(n // 10, 1)], "mid10_50": order[max(n // 10, 1):n // 2], "bottom50": order[n // 2:]}
