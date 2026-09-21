"""Storage-side evaluation: is this any good as a STORE, against things built to be stores?

codec     Stored representation size and reconstruction quality against Opus and AAC at matched
          bitrate (ffmpeg). "Stored representation" is stated two ways, because which one is fair
          is arguable: the synaptic state alone (late-phase weights, 8 bits each), and that plus the
          linear readout (16 bits per weight) without which the state cannot be played back.
          Quality is the SAME metric for both sides: band-envelope correlation with the original.
          Video / event-camera comparison: unavailable (the retina front end is a later milestone).
salience  Rare-event retention. One rare loud event inside a long ordinary stream: does the
          salience-gated network keep the event window better than a UNIFORM compressor given the
          same storage budget, and better than itself with NM held flat?

Both report honestly if the system loses. It is expected to lose the codec comparison: Opus is an
engineered codec and this is a recurrent network read out linearly.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from ..config import Config
from ..decode import readout as ro
from ..frontend.filterbank import analyse
from ..frontend.io import Stream
from . import common as C

CODEC_MIN_KBPS = {"libopus": 6.0, "aac": 8.0}


def codec_roundtrip(x: np.ndarray, fs: float, codec: str, kbps: float) -> tuple[np.ndarray, float]:
    """Encode + decode with ffmpeg. Returns (decoded waveform at fs, ACTUAL bitrate from file size)."""
    ext = {"libopus": "ogg", "aac": "m4a"}[codec]
    with tempfile.TemporaryDirectory() as d:
        src, enc, dec = Path(d) / "in.wav", Path(d) / f"enc.{ext}", Path(d) / "out.wav"
        sf.write(src, x.astype(np.float32), int(fs))
        args = ["-application", "voip"] if codec == "libopus" else []
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ac", "1", "-c:a", codec, "-b:a",
                        f"{kbps}k", *args, str(enc)], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(enc), "-ar", str(int(fs)), "-ac", "1", str(dec)], check=True)
        y, _ = sf.read(dec, dtype="float64")
        actual = enc.stat().st_size * 8 / (x.size / fs) / 1000.0
    n = min(x.size, y.size)
    out = np.zeros_like(x); out[:n] = y[:n]
    return out, actual


def envelope_r(x: np.ndarray, y: np.ndarray, fs: float, cfg: Config, window_s=None) -> float:
    ex = analyse(Stream("a", x, fs, ""), cfg.frontend, keep_fine=False).env
    ey = analyse(Stream("b", y, fs, ""), cfg.frontend, keep_fine=False).env
    a = ro.resample_targets(ex[None], cfg.frontend.envelope_rate_hz, cfg.decode.rate_hz)
    b = ro.resample_targets(ey[None], cfg.frontend.envelope_rate_hz, cfg.decode.rate_hz)
    if window_s:
        k0, k1 = (int(w * cfg.decode.rate_hz) for w in window_s); a, b = a[k0:k1], b[k0:k1]
    return ro.mean_corr(b, a)


def _rare_event_stream(seconds: float, seed: int, fs=16000.0) -> tuple[Stream, float]:
    rng = np.random.default_rng(seed + 31); t = np.arange(int(seconds * fs)) / fs
    bg = 0.15 * rng.standard_normal(t.size) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.7 * t + rng.uniform(0, 6)))
    t_ev = float(rng.uniform(0.4, 0.7) * seconds)
    sel = (t >= t_ev) & (t < t_ev + 0.5)
    chord = sum(np.sin(2 * np.pi * f * t[sel]) for f in (440.0, 660.0, 990.0, 1485.0))
    x = bg.copy(); x[sel] += 0.9 * chord / 4 * np.hanning(sel.sum())
    return Stream("rare_event", x / np.abs(x).max(), fs, "synthetic:rare_event"), t_ev


def _storage_worker(job):
    try:
        from ..network import build_inputs, simulate
        from ..recall.evaluate import evaluate
        from ..frontend.io import synthetic_streams
        cfg = Config.model_validate(job["cfg"])
        if job["kind"] == "salience":
            stream, t_ev = _rare_event_stream(cfg.protocol.encode_s, cfg.seed)
        else:
            stream, t_ev = synthetic_streams(1, cfg.protocol.encode_s, seed=cfg.seed)[0], None
        inputs = build_inputs([stream], cfg); res = simulate(cfg, inputs); ev, dec = evaluate(res, inputs, cfg)
        bits_state = res.extra["n_ee"] * 8
        bits_full = bits_state + dec.W.size * 16
        out = dict(ok=True, tag=job["tag"], seed=cfg.seed, recall_r=ev["recall"][-1]["guarded_r"][0],
                   encode_r=ev["encode_heldout_r"][0], kbps_state=bits_state / cfg.protocol.encode_s / 1e3,
                   kbps_full=bits_full / cfg.protocol.encode_s / 1e3, codecs={})
        x = stream.x[:int(cfg.protocol.encode_s * stream.fs)]
        win = (max(t_ev - 0.25, 0), t_ev + 0.75) if t_ev is not None else None
        if win is not None:                                   # event-window recall for the network
            seg = res.timeline.recalls()[-1]
            Y = ro.resample_targets(inputs.env, inputs.env_rate, cfg.decode.rate_hz)
            Xr = ro.activity_features(*res.spikes_e, res.n_exc, seg.t0, seg.t1, cfg.decode.rate_hz, cfg.decode.filter_tau_ms)
            k0, k1 = (int(w * cfg.decode.rate_hz) for w in win)
            out["event_recall_r"] = ro.mean_corr(dec.predict(Xr)[k0:k1], Y[k0:k1])
            i, t = res.spikes_e; enc = res.timeline.segment("encode")
            active = np.unique(i[(t >= enc.t0 + win[0]) & (t < enc.t0 + win[1])])
            z = np.abs(res.z_final); on = np.isin(res.syn_j, active)
            out["late_weight_share_event_cells"] = float(z[on].sum() / (z.sum() + 1e-12))
            out["chance_share"] = float(on.mean()); out["t_event_s"] = t_ev
        for codec, kmin in CODEC_MIN_KBPS.items():
            for budget, kb in (("state", out["kbps_state"]), ("full", out["kbps_full"])):
                use = max(kb, kmin)
                y, actual = codec_roundtrip(x, stream.fs, codec, use)
                out["codecs"][f"{codec}@{budget}"] = dict(requested_kbps=kb, used_kbps=use, actual_kbps=actual,
                                                          floor_hit=bool(kb < kmin), r=envelope_r(x, y, stream.fs, cfg),
                                                          event_r=envelope_r(x, y, stream.fs, cfg, win) if win else None)
        return out
    except Exception as ex:
        import traceback
        return dict(ok=False, tag=job["tag"], seed=job["cfg"]["seed"], error=f"{type(ex).__name__}: {ex}", trace=traceback.format_exc()[-900:])


def _run(cfg, seeds, workers, kind, conds):
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import get_context
    jobs = []
    for tag, c in conds.items():
        for s in seeds:
            cc = c.model_copy(deep=True); cc.seed = int(s); jobs.append(dict(cfg=cc.model_dump(), tag=tag, kind=kind))
    with ProcessPoolExecutor(max(workers, 1), mp_context=get_context("spawn")) as ex:
        return list(ex.map(_storage_worker, jobs))


def exp_codec(cfg: Config, seeds, workers):
    out = C.results_dir("codec_comparison"); runs = _run(cfg, seeds, workers, "codec", {"full": cfg}); ok = [r for r in runs if r["ok"]]
    rep = "## Stored size and quality vs Opus / AAC at matched bitrate\n\n"
    summ = {}
    if ok:
        net_rec, net_enc = C.ci95([r["recall_r"] for r in ok]), C.ci95([r["encode_r"] for r in ok])
        rep += (f"Network: encode held-out r {C.fmt(net_enc)}; RECALL r after the last delay {C.fmt(net_rec)}.\n"
                f"Stored size: synaptic state {np.mean([r['kbps_state'] for r in ok]):.2f} kbps; with readout "
                f"{np.mean([r['kbps_full'] for r in ok]):.2f} kbps.\n\n| codec @ budget | bitrate actually used (kbps) | floor hit | envelope r | network recall - codec |\n|---|---|---|---|---|\n")
        for key in ok[0]["codecs"]:
            cr = C.ci95([r["codecs"][key]["r"] for r in ok]); d = C.paired_diff([r["recall_r"] for r in ok], [r["codecs"][key]["r"] for r in ok])
            rep += (f"| {key} | {np.mean([r['codecs'][key]['actual_kbps'] for r in ok]):.2f} | {ok[0]['codecs'][key]['floor_hit']} | {C.fmt(cr)} | "
                    f"{C.fmt(d)} {'network WINS' if d['beats'] else 'network LOSES or ties'} |\n")
            summ[key] = dict(codec=cr, diff=d)
        rep += "\nWhere `floor hit` is True the codec could not go as low as the network's budget, so it was given MORE bits than the network.\n"
    rep += "\nVideo / event-camera encoding: **unavailable** -- no retina front end is built (later milestone).\n"
    C.save(out, cfg, runs, summ, rep); return out


def exp_salience(cfg: Config, seeds, workers):
    out = C.results_dir("salience_retention")
    flat = cfg.model_copy(deep=True); flat.mechanisms.nm_dynamic = False
    runs = _run(cfg, seeds, workers, "salience", {"salience_gated": cfg, "flat_nm": flat})
    g = {t: [r for r in runs if r["ok"] and r["tag"] == t] for t in ("salience_gated", "flat_nm")}
    rep = "## Salience-gated retention of a rare event\n\n| system | event-window r | whole-stream r |\n|---|---|---|\n"
    for t, rs in g.items():
        rep += f"| network, {t} | {C.fmt(C.ci95([r['event_recall_r'] for r in rs]))} | {C.fmt(C.ci95([r['recall_r'] for r in rs]))} |\n"
    sg = g["salience_gated"]
    summ = {}
    if sg:
        for key in sg[0]["codecs"]:
            rep += f"| uniform: {key} | {C.fmt(C.ci95([r['codecs'][key]['event_r'] for r in sg]))} | {C.fmt(C.ci95([r['codecs'][key]['r'] for r in sg]))} |\n"
        d_nm = C.paired_diff([r["event_recall_r"] for r in sg], [r["event_recall_r"] for r in g["flat_nm"]])
        d_op = C.paired_diff([r["event_recall_r"] for r in sg], [r["codecs"]["libopus@state"]["event_r"] for r in sg])
        share = C.ci95([r["late_weight_share_event_cells"] - r["chance_share"] for r in sg])
        rep += (f"\n- gated vs flat NM, event window: {C.fmt(d_nm)} -> {'gating HELPS' if d_nm['beats'] else 'no detectable benefit'}\n"
                f"- gated network vs uniform Opus at the state budget, event window: {C.fmt(d_op)} -> {'network WINS' if d_op['beats'] else 'network LOSES or ties'}\n"
                f"- late-phase weight landing on event-active cells, above chance share: {C.fmt(share)}\n")
        summ = dict(gated_vs_flat=d_nm, gated_vs_opus=d_op, late_share_above_chance=share)
    C.save(out, cfg, runs, summ, rep); return out
