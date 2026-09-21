"""Population-signal outputs: an LFP/EEG proxy, temporal response functions, and the
phase-lag-versus-frequency test that separates EVOKED tracking from ENTRAINED tracking.

LFP proxy. Summed synaptic currents onto the excitatory cells. Two forms are returned:
  sum_abs   |I_exc| + |I_inh|
  rws       |I_exc|(t - 6 ms) + 1.65 |I_inh|(t), the reference weighted sum of Mazzoni, Linden,
            Cuntz, Lansner, Panzeri & Einevoll 2015, PLoS Comput Biol 11:e1004584. The 6 ms and 1.65
            are CITED FROM MEMORY (ASSUMPTIONS.md); that paper fitted them for LIF point-neuron
            networks against a morphological model, which is this use case.
A point-neuron network has no geometry, so this is a proxy for the shape of the signal, never
its amplitude or polarity at an electrode.

TRF. Ridge-regularised lagged regression from the stimulus envelope to the proxy -- the forward
model of Crosse, Di Liberto, Bednar & Lalor 2016, Front Hum Neurosci 10:604 (mTRF toolbox),
written directly here (no toolbox dependency).

Published benchmark (read in full this build): Doelling, Assaneo, Bevilacqua, Pesaran & Poeppel
2019, PNAS 116:10113. Phase concentration metric PCM = |mean over note rates of exp(i*lag)| for
rates 1-8 notes/s. Their evoked-response model gives PCM 0.245 (0.17 over 0.5-8), their
Wilson-Cowan oscillator 0.58 (0.66), and MEG sits at 95% CI (0.30, 0.57) left / (0.35, 0.59)
right. ``pcm_verdict`` places a measured PCM against those three numbers and nothing else.
"""
from __future__ import annotations

import numpy as np
from scipy import signal

DOELLING_2019 = dict(pcm_evoked=0.245, pcm_oscillator=0.58, meg_ci_left=(0.30, 0.57),
                     meg_ci_right=(0.35, 0.59), rates_nps=(1.0, 1.5, 5.0, 8.0),
                     doi="10.1073/pnas.1816414116")


def lfp_proxy(Ie_pA: np.ndarray, Ii_pA: np.ndarray, fs: float = 1000.0, Irec_pA: np.ndarray | None = None) -> dict[str, np.ndarray]:
    """``rws_recurrent`` drops the AFFERENT current. Measured here: with the afferent term in, the
    proxy tracks the stimulus at PLV 0.999 with a 7 ms lag whatever the network does, because it is
    mostly the input arriving -- so it cannot tell an evoked network from an entrained one."""
    d = int(round(0.006 * fs))
    sh = lambda a: np.concatenate([np.full(d, a[0]), a[:-d]]) if d else a
    ae, ai = np.abs(Ie_pA), np.abs(Ii_pA)
    out = {"sum_abs": ae + ai, "rws": sh(ae) + 1.65 * ai}
    if Irec_pA is not None:
        out["rws_recurrent"] = sh(np.abs(Irec_pA)) + 1.65 * ai
    return out


def _z(x):
    return (x - x.mean()) / (x.std() + 1e-12)


def fit_trf(stim: np.ndarray, resp: np.ndarray, fs: float, tmin_s=-0.1, tmax_s=0.5, alpha=1.0):
    """Forward TRF. Returns (lags_s, weights, r_heldout) with the last 20% held out."""
    stim, resp = _z(stim), _z(resp)
    lags = np.arange(int(tmin_s * fs), int(tmax_s * fs) + 1)
    X = np.zeros((stim.size, lags.size))
    for c, L in enumerate(lags):
        if L >= 0:
            X[L:, c] = stim[:stim.size - L]
        else:
            X[:L, c] = stim[-L:]
    n = int(0.8 * stim.size)
    A = X[:n].T @ X[:n] + alpha * n * np.eye(lags.size)
    w = np.linalg.solve(A, X[:n].T @ resp[:n])
    pred = X[n:] @ w
    r = float(np.corrcoef(pred, resp[n:])[0, 1]) if pred.std() > 0 else float("nan")
    return lags / fs, w, r


def phase_lag(stim: np.ndarray, resp: np.ndarray, fs: float, f_hz: float, bw_hz: float | None = None):
    """Circular-mean phase lag (resp behind stim, radians in (-pi, pi]) and coupling strength at f."""
    bw = bw_hz or max(0.3 * f_hz, 0.3)
    sos = signal.butter(2, [max(f_hz - bw, 0.05), f_hz + bw], btype="band", fs=fs, output="sos")
    a = signal.hilbert(signal.sosfiltfilt(sos, _z(stim)))
    b = signal.hilbert(signal.sosfiltfilt(sos, _z(resp)))
    k = int(fs / f_hz)                                  # drop one cycle of edge at each end
    v = np.exp(1j * (np.angle(a[k:-k]) - np.angle(b[k:-k]))).mean()
    return float(np.angle(v)), float(np.abs(v))


def pcm(lags_rad) -> float:
    """Phase concentration metric: length of the mean unit vector over stimulus rates."""
    return float(np.abs(np.mean(np.exp(1j * np.asarray(lags_rad)))))


def pcm_verdict(value: float) -> str:
    lo = min(DOELLING_2019["meg_ci_left"][0], DOELLING_2019["meg_ci_right"][0])
    hi = max(DOELLING_2019["meg_ci_left"][1], DOELLING_2019["meg_ci_right"][1])
    where = "inside" if lo <= value <= hi else ("below" if value < lo else "above")
    nearer = "evoked" if abs(value - DOELLING_2019["pcm_evoked"]) < abs(value - DOELLING_2019["pcm_oscillator"]) else "oscillator"
    return (f"PCM {value:.3f} is {where} the published MEG 95% CI envelope ({lo:.2f}-{hi:.2f}) and nearer the "
            f"published {nearer}-model value")


def pcm_is_informative(latency_ms: float, f_max_hz: float = 8.0) -> bool:
    """A fixed latency L spreads phase lags over 2*pi*L*(f_max - f_min). Below ~a quarter cycle of
    spread the evoked and oscillator accounts predict the SAME high PCM, and the test says nothing."""
    return abs(latency_ms) * 1e-3 * (f_max_hz - 1.0) >= 0.25


def effective_latency_ms(freqs_hz, lags_rad) -> float:
    """Slope of unwrapped phase lag against frequency = a fixed latency, if tracking is evoked."""
    ph = np.unwrap(np.asarray(lags_rad))
    return float(np.polyfit(np.asarray(freqs_hz), ph, 1)[0] / (2 * np.pi) * 1e3)


def theta_locking(lfp: np.ndarray, envs: np.ndarray, fs: float, f_theta: float) -> list[dict]:
    """Per stream: phase-locking value between theta-band LFP and that stream's theta-band envelope."""
    out = []
    for e in envs:
        lag, plv = phase_lag(e, lfp, fs, f_theta, bw_hz=2.0)
        out.append(dict(plv=plv, lag_rad=lag))
    return out
