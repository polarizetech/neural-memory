"""The experiments. One CLI command each; every one reports mean +/- 95% CI over seeds and states
plainly when a mechanism does not beat its ablation or the reservoir baseline.

  delay       1. one stream: reconstruction correlation vs delay after encoding
  streams     2. two and three simultaneous streams: per-stream r, crosstalk, identity from rank
  ablations   3. single-mechanism ablations (+ filterbank front end, + frozen-weight reservoir)
  baselines   4. echo state network, shuffled-input control, raw-input upper bound
  lehr        5. Lehr et al. 2022 NM sweep reproduction      (experiments/lehr.py)
  population  LFP proxy + TRF + phase lag vs frequency, theta free (evoked) vs reset (entrained)
  attention   two streams, attend one via NM gain: theta locking and recall smear
  codec       stored size and quality vs Opus / AAC at matched bitrate
  salience    rare-event retention vs uniform compression at the same budget
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from ..config import Config
from . import common as C

ABLATIONS = {
    "no_t_current": ("mechanisms", "t_current"), "no_gap_junctions": ("mechanisms", "gap_junctions"),
    "flat_nm": ("mechanisms", "nm_dynamic"), "no_tagging": ("mechanisms", "tagging"),
    "no_creb": ("mechanisms", "creb"), "no_tonic_drift": ("mechanisms", "tonic_drift"),
    "no_theta": ("mechanisms", "theta"), "frozen_weights_reservoir": ("mechanisms", "plasticity"),
}


def ablated(cfg: Config, name: str) -> Config:
    c = cfg.model_copy(deep=True)
    if name == "filterbank_frontend":
        c.frontend.kind = "filterbank"
    else:
        sect, key = ABLATIONS[name]
        setattr(getattr(c, sect), key, False)
    return c


def _recall_r(run: dict, k: int = -1, stream: int = 0) -> float:
    """PRIMARY recall score: the GUARDED window (1 s after cue offset onward)."""
    return run["recall"][k]["guarded_r"][stream]


def _table(rows: list[tuple]) -> str:
    head = "| " + " | ".join(rows[0]) + " |\n|" + "---|" * len(rows[0]) + "\n"
    return head + "".join("| " + " | ".join(str(x) for x in r) + " |\n" for r in rows[1:])


# ------------------------------------------------------------------ 1. delay
def exp_delay(cfg: Config, seeds, workers, streams=None):
    out = C.results_dir("exp1_delay")
    c = cfg.model_copy(deep=True)
    runs = C.run_jobs(C.jobs_for({"full": c}, seeds, streams or {"n": 1}, esn=True, raw=True), workers)
    g = C.by_tag(runs).get("full", [])
    delays = [r["delay_s"] for r in g[0]["recall"]] if g else []
    rows, summ = [("delay (sim s)", "bio-equivalent", "spiking r, UNGUARDED (includes cue carry-over)", "spiking r, guarded", "ESN r, guarded", "spiking - ESN (guarded)", "best-lag p<0.05 (seeds)")], {}
    for k, d in enumerate(delays):
        a = [x["recall"][k]["guarded_r"][0] for x in g]; e = [x["esn"]["recall"][k]["guarded_r"][0] for x in g]
        un = C.ci95([x["recall"][k]["locked_r"][0] for x in g])
        sig = sum(x["recall"][k]["bestlag"]["p"] < 0.05 for x in g)
        ca, ce, df = C.ci95(a), C.ci95(e), C.paired_diff(a, e)
        summ[str(d)] = dict(spiking=ca, esn=ce, diff=df, n_sig=sig, unguarded=un)
        rows.append((d, f"{d * c.time_compression / 60:.0f} min", C.fmt(un), C.fmt(ca), C.fmt(ce),
                     C.fmt(df) + (" BEATS" if df["beats"] else " does not beat"), f"{sig}/{len(g)}"))
    enc = C.ci95([x["encode_heldout_r"][0] for x in g]); raw = C.ci95([x["raw_input_r"][0] for x in g])
    fig, ax = plt.subplots(figsize=(6, 3.6))
    for key, col in (("spiking", "C0"), ("esn", "C1")):
        m = [summ[str(d)][key]["mean"] for d in delays]
        ax.errorbar(delays, m, yerr=[[mm - summ[str(d)][key]["lo"] for mm, d in zip(m, delays)],
                                     [summ[str(d)][key]["hi"] - mm for mm, d in zip(m, delays)]], marker="o", label=key, color=col)
    ax.axhline(0, color="0.6", lw=0.8); ax.set_xscale("log"); ax.set_xlabel("delay after encoding (simulated s)")
    ax.set_ylabel("recall reconstruction r (time-locked)"); ax.legend(); C.stamp_figure(fig, c); fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out / "delay.png", dpi=130); plt.close(fig)
    rep = (f"## Experiment 1 -- reconstruction vs delay (one stream, recall mode `{c.protocol.recall_mode}`)\n\n"
           f"Encode held-out r: {C.fmt(enc)}; raw-input upper bound: {C.fmt(raw)}.\n\n" + _table(rows) +
           "\nRecall is scored on the GUARDED window (from 1 s after cue offset). The unguarded column is kept because the "
           "first pass of this experiment scored +0.045 there at EVERY delay -- carry-over of the cue, not storage.\n"
           "Probes share one timeline, so an earlier probe can alter a later one.\n")
    C.save(out, c, runs, dict(encode=enc, raw=raw, delays=summ), rep)
    return out


# ------------------------------------------------------------------ 2. streams
def exp_streams(cfg: Config, seeds, workers):
    out = C.results_dir("exp2_streams")
    jobs = []
    for n in (2, 3):
        jobs += C.jobs_for({f"{n}_streams": cfg}, seeds, {"n": n}, esn=True)
    runs = C.run_jobs(jobs, workers); g = C.by_tag(runs)
    rep, summ = "## Experiment 2 -- simultaneous streams\n\n", {}
    for tag, rs in g.items():
        S = rs[0]["n_streams"]
        encC = np.mean([r["encode_crosstalk"] for r in rs], axis=0); recC = np.mean([r["recall"][-1]["crosstalk"] for r in rs], axis=0)
        rows = [("stream", "encode held-out r", "recall r (last delay)", "ESN recall r")]
        for s in range(S):
            rows.append((s, C.fmt(C.ci95([r["encode_heldout_r"][s] for r in rs])), C.fmt(C.ci95([_recall_r(r, -1, s) for r in rs])),
                         C.fmt(C.ci95([r["esn"]["recall"][-1]["guarded_r"][s] for r in rs]))))
        idr = [r["stream_identity"] for r in rs if "stream_identity" in r]
        rep += f"### {tag}\n\n" + _table(rows) + f"\nEncode crosstalk (rows decoded, cols true):\n\n```\n{np.round(encC, 3)}\n```\nRecall crosstalk:\n\n```\n{np.round(recC, 3)}\n```\n"
        if idr:
            for feat in ("rank", "fired"):
                acc = C.ci95([x[feat]["acc"] for x in idr]); nul = C.ci95([x[feat]["null_p95"] for x in idr])
                ok = sum(x[feat]["p"] < 0.05 for x in idr)
                rep += f"- stream identity from **{feat}**: accuracy {C.fmt(acc)}; permutation-null 95th pct {C.fmt(nul)}; p<0.05 in {ok}/{len(idr)} seeds\n"
        summ[tag] = dict(encode_crosstalk=encC.tolist(), recall_crosstalk=recC.tolist())
        rep += "\n"
    C.save(out, cfg, runs, summ, rep)
    return out


# ------------------------------------------------------------------ 3. ablations
def exp_ablations(cfg: Config, seeds, workers, n_streams=2):
    out = C.results_dir("exp3_ablations")
    conds = {"full": cfg, **{name: ablated(cfg, name) for name in list(ABLATIONS) + ["filterbank_frontend"]}}
    runs = C.run_jobs(C.jobs_for(conds, seeds, {"n": n_streams}, esn=False), workers); g = C.by_tag(runs)
    rows, summ = [("condition", "encode held-out r", "recall r (last delay)", "full - this (recall)", "verdict")], {}
    full = [_recall_r(r) for r in g.get("full", [])]
    for tag, rs in g.items():
        e = C.ci95([np.mean(r["encode_heldout_r"]) for r in rs]); rc = [_recall_r(r) for r in rs]
        d = C.paired_diff(full, rc) if tag != "full" else None
        verdict = "-" if d is None else ("mechanism HELPS recall" if d["beats"] else
                                         ("ablation is BETTER" if np.isfinite(d["hi"]) and d["hi"] < 0 else "no detectable effect"))
        rows.append((tag, C.fmt(e), C.fmt(C.ci95(rc)), "-" if d is None else C.fmt(d), verdict))
        summ[tag] = dict(encode=e, recall=C.ci95(rc), full_minus_this=d,
                         state_frac=np.mean([r["state_frac_encode"] for r in rs], axis=0).tolist(),
                         frac_late=C.ci95([r["frac_late"] for r in rs]))
    rep = ("## Experiment 3 -- single-mechanism ablations\n\nA mechanism is said to help ONLY if the whole 95% CI of "
           "(full - ablated) is above zero.\n\n" + _table(rows))
    C.save(out, cfg, runs, summ, rep)
    return out


# ------------------------------------------------------------------ 4. baselines
def exp_baselines(cfg: Config, seeds, workers, n_streams=2):
    out = C.results_dir("exp4_baselines")
    shuf = cfg.model_copy(deep=True); shuf.protocol.shuffle_input = True
    runs = C.run_jobs(C.jobs_for({"full": cfg, "shuffled_input": shuf}, seeds, {"n": n_streams}, esn=True, raw=True), workers)
    g = C.by_tag(runs); f = g.get("full", []); s = g.get("shuffled_input", [])
    m = lambda rs, fn: C.ci95([fn(r) for r in rs])
    rows = [("system", "encode held-out r", "recall r (last delay)"),
            ("spiking network (full)", C.fmt(m(f, lambda r: np.mean(r["encode_heldout_r"]))), C.fmt(m(f, _recall_r))),
            ("echo state network, equal units", C.fmt(m(f, lambda r: np.mean(r["esn"]["encode_heldout_r"]))), C.fmt(m(f, lambda r: r["esn"]["recall"][-1]["guarded_r"][0]))),
            ("shuffled-input control (floor)", C.fmt(m(s, lambda r: np.mean(r["encode_heldout_r"]))), C.fmt(m(s, _recall_r))),
            ("decoder on raw input (upper bound)", C.fmt(m(f, lambda r: np.mean(r["raw_input_r"]))), "n/a")]
    d_enc = C.paired_diff([np.mean(r["encode_heldout_r"]) for r in f], [np.mean(r["esn"]["encode_heldout_r"]) for r in f])
    d_rec = C.paired_diff([_recall_r(r) for r in f], [r["esn"]["recall"][-1]["guarded_r"][0] for r in f])
    rep = ("## Experiment 4 -- baselines\n\n" + _table(rows) +
           f"\n- spiking - ESN, encode: {C.fmt(d_enc)} -> {'beats' if d_enc['beats'] else 'DOES NOT beat'} the reservoir\n"
           f"- spiking - ESN, recall: {C.fmt(d_rec)} -> {'beats' if d_rec['beats'] else 'DOES NOT beat'} the reservoir\n")
    C.save(out, cfg, runs, dict(encode_diff=d_enc, recall_diff=d_rec), rep)
    return out


# ------------------------------------------------------------------ population / theta
def _am_stream(rate_hz: float, seconds: float, fs=16000.0, seed=0):
    from ..frontend.io import Stream
    rng = np.random.default_rng(seed); t = np.arange(int(seconds * fs)) / fs
    # raised-cosine "notes" at rate_hz on a noise carrier: sharp-ish attacks, as in a note sequence
    ph = (t * rate_hz) % 1.0
    env = np.where(ph < 0.6, 0.5 * (1 - np.cos(2 * np.pi * np.clip(ph / 0.6, 0, 1))), 0.0)
    return Stream(f"notes_{rate_hz:g}nps", rng.standard_normal(t.size) * env, fs, f"synthetic:notes_{rate_hz:g}nps")


def _population_worker(job):
    try:
        from ..network import build_inputs, simulate
        from ..decode import population as pop
        from ..recall.evaluate import evaluate
        cfg = Config.model_validate(job["cfg"])
        inputs = build_inputs([_am_stream(job["rate"], cfg.protocol.encode_s, seed=cfg.seed)], cfg)
        res = simulate(cfg, inputs); ev, _ = evaluate(res, inputs, cfg)
        enc = res.timeline.segment("encode"); sel = (res.lfp_t >= enc.t0) & (res.lfp_t < enc.t1)
        prox = pop.lfp_proxy(res.lfp_Ie[sel], res.lfp_Ii[sel], Irec_pA=res.lfp_Ir[sel]); e = inputs.env.mean(axis=(0, 1)); m = min(sel.sum(), e.size)
        lag, plv = pop.phase_lag(e[:m], prox["rws_recurrent"][:m], inputs.env_rate, job["rate"])     # PRIMARY: recurrent-only
        lag_a, plv_a = pop.phase_lag(e[:m], prox["rws"][:m], inputs.env_rate, job["rate"])          # with the afferent current
        return dict(ok=True, tag=job["tag"], seed=cfg.seed, rate=job["rate"], lag=lag, plv=plv, lag_afferent=lag_a, plv_afferent=plv_a,
                    ordering=ev["recall"][-1]["ordering_rho"], recall_r=ev["recall"][-1]["locked_r"][0], trf=ev["trf"])
    except Exception as ex:
        import traceback
        return dict(ok=False, tag=job["tag"], seed=job["cfg"]["seed"], error=f"{type(ex).__name__}: {ex}", trace=traceback.format_exc()[-800:])


def exp_population(cfg: Config, seeds, workers):
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import get_context
    from ..decode.population import DOELLING_2019 as D, pcm, pcm_verdict, effective_latency_ms, pcm_is_informative
    out = C.results_dir("population_theta")
    jobs = []
    for mode in ("free", "reset"):
        c = cfg.model_copy(deep=True); c.theta.mode = mode
        c.protocol.recall_delays_s = [min(cfg.protocol.recall_delays_s)]   # phase lag is an ENCODE-phase measure
        for rate in D["rates_nps"]:
            for s in seeds:
                cc = c.model_copy(deep=True); cc.seed = int(s)
                jobs.append(dict(cfg=cc.model_dump(), tag=mode, rate=rate))
    with ProcessPoolExecutor(max(workers, 1), mp_context=get_context("spawn")) as ex:
        runs = list(ex.map(_population_worker, jobs))
    rep = ("## Population signal -- evoked (theta free) vs entrained (theta phase-reset on onsets)\n\n"
           f"Benchmark: Doelling et al. 2019 (doi:{D['doi']}), note rates {D['rates_nps']} nps. Published PCM: evoked model "
           f"{D['pcm_evoked']}, oscillator model {D['pcm_oscillator']}, MEG 95% CI {D['meg_ci_left']} (L) / {D['meg_ci_right']} (R).\n\n")
    summ = {}
    fig, ax = plt.subplots(figsize=(6, 3.6))
    for mode in ("free", "reset"):
        ok = [r for r in runs if r["ok"] and r["tag"] == mode]
        per_seed = []
        for s in seeds:
            lags = [r["lag"] for r in ok if r["seed"] == s]
            if len(lags) == len(D["rates_nps"]):
                per_seed.append(pcm(lags))
        mean_lag = [float(np.angle(np.mean(np.exp(1j * np.array([r["lag"] for r in ok if r["rate"] == f]))))) for f in D["rates_nps"]]
        c_pcm = C.ci95(per_seed); lat = effective_latency_ms(D["rates_nps"], mean_lag)
        summ[mode] = dict(pcm=c_pcm, mean_lag_rad=mean_lag, latency_ms=lat, ordering=C.ci95([r["ordering"] for r in ok]),
                          recall_r=C.ci95([r["recall_r"] for r in ok]), plv=C.ci95([r["plv"] for r in ok]))
        lag_aff = [float(np.angle(np.mean(np.exp(1j * np.array([r["lag_afferent"] for r in ok if r["rate"] == f]))))) for f in D["rates_nps"]]
        summ[mode].update(informative=pcm_is_informative(lat), pcm_with_afferent=pcm(lag_aff), latency_with_afferent_ms=effective_latency_ms(D["rates_nps"], lag_aff))
        rep += (f"### theta `{mode}`\n- LFP proxy = RECURRENT + inhibitory currents (afferent current excluded). With the afferent current "
                f"included the proxy is mostly the input itself: PCM {summ[mode]['pcm_with_afferent']:.3f}, latency {summ[mode]['latency_with_afferent_ms']:.0f} ms.\n"
                f"- PCM test informative at this latency: **{'yes' if summ[mode]['informative'] else 'NO -- the latency is too short for evoked and oscillator accounts to predict different PCM; read nothing into the PCM verdict below'}**\n"
                f"- PCM over rates: {C.fmt(c_pcm)} -- {pcm_verdict(c_pcm['mean'])}\n"
                f"- phase lag by rate (rad): {dict(zip(D['rates_nps'], np.round(mean_lag, 2)))}; slope = {lat:.0f} ms effective latency\n"
                f"- stimulus-LFP coupling (PLV): {C.fmt(summ[mode]['plv'])}\n"
                f"- recall ORDERING (Spearman rho): {C.fmt(summ[mode]['ordering'])}; recall r: {C.fmt(summ[mode]['recall_r'])}\n\n")
        ax.plot(D["rates_nps"], np.unwrap(mean_lag), marker="o", label=f"theta {mode}")
    ax.set_xlabel("note rate (per s)"); ax.set_ylabel("phase lag, response behind stimulus (rad)"); ax.legend()
    C.stamp_figure(fig, cfg, "LFP proxy = reference weighted sum of synaptic currents"); fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out / "phase_lag.png", dpi=130); plt.close(fig)
    C.save(out, cfg, runs, summ, rep)
    return out


# ------------------------------------------------------------------ attention
def exp_attention(cfg: Config, seeds, workers):
    out = C.results_dir("attention_two_stream")
    att = cfg.model_copy(deep=True); att.attention.stream = 0
    runs = C.run_jobs(C.jobs_for({"no_attention": cfg, "attend_stream0": att}, seeds, {"n": 2}), workers); g = C.by_tag(runs)
    rows = [("condition", "theta PLV s0", "theta PLV s1", "recall r s0", "recall r s1", "smear ms (cued s0)")]
    summ = {}
    for tag, rs in g.items():
        v = dict(plv0=C.ci95([r["theta_locking"][0]["plv"] for r in rs]), plv1=C.ci95([r["theta_locking"][1]["plv"] for r in rs]),
                 r0=C.ci95([_recall_r(r, -1, 0) for r in rs]), r1=C.ci95([_recall_r(r, -1, 1) for r in rs]),
                 smear=C.ci95([r["recall"][-1]["bestlag"]["smear_ms"] for r in rs]))
        summ[tag] = v; rows.append((tag, *(C.fmt(v[k]) for k in ("plv0", "plv1", "r0", "r1", "smear"))))
    a, n = g.get("attend_stream0", []), g.get("no_attention", [])
    d_plv = C.paired_diff([r["theta_locking"][0]["plv"] - r["theta_locking"][1]["plv"] for r in a],
                          [r["theta_locking"][0]["plv"] - r["theta_locking"][1]["plv"] for r in n])
    d_sm = C.paired_diff([r["recall"][-1]["bestlag"]["smear_ms"] for r in n], [r["recall"][-1]["bestlag"]["smear_ms"] for r in a])
    rep = ("## Attention -- attend stream 0 via NM gain\n\n" + _table(rows) +
           f"\n- attention shifts theta locking toward the attended stream: {C.fmt(d_plv)} -> {'YES' if (d_plv['beats'] and d_plv['mean'] >= 0.05) else ('detected but NEGLIGIBLE (< 0.05 PLV): a CI clear of zero is not an effect size' if d_plv['beats'] else 'NOT DETECTED')}\n"
           f"- attended recall is less smeared (smear reduction, ms): {C.fmt(d_sm)} -> {'YES' if d_sm['beats'] else 'NOT DETECTED'}\n")
    C.save(out, cfg, runs, dict(conditions=summ, plv_shift=d_plv, smear_reduction=d_sm), rep)
    return out


# ------------------------------------------------------------------ recall modes
N_FOREIGN = 20


def _recall_modes_worker(job):
    """One run, plus the FOREIGN-STIMULUS null: is decoded recall closer to ITS stream than to 20 other
    streams from the same generator? For uncued modes the circular-shift null is degenerate (the lag search
    spans the record, so a shifted copy is searched over the same alignments), and this one is not."""
    try:
        from ..network import build_inputs, simulate
        from ..recall.evaluate import evaluate
        from ..decode import baselines, readout as ro
        from ..frontend.filterbank import analyse
        from ..frontend.io import synthetic_streams
        cfg = Config.model_validate(job["cfg"]); dc = cfg.decode
        inputs = build_inputs(C.get_streams({"n": 1}, cfg), cfg); res = simulate(cfg, inputs)
        out, dec = evaluate(res, inputs, cfg)
        Y = ro.resample_targets(inputs.env, inputs.env_rate, dc.rate_hz)
        out["esn"] = baselines.esn_evaluate(inputs, res.timeline, cfg, Y, cfg.seed)
        foreign = [ro.resample_targets(analyse(synthetic_streams(1, cfg.protocol.encode_s, seed=10_000 + cfg.seed * 100 + j)[0],
                                               cfg.frontend, seconds=cfg.protocol.encode_s, keep_fine=False).env[None], inputs.env_rate, dc.rate_hz)
                   for j in range(N_FOREIGN)]
        max_lag = int((1.0 if cfg.protocol.cued else min(0.5 * (cfg.protocol.recall_s or cfg.protocol.encode_s), 5.0)) * dc.rate_hz)
        for rec, seg in zip(out["recall"], res.timeline.recalls()):
            X = ro.activity_features(*res.spikes_e, res.n_exc, seg.t0, seg.t1, dc.rate_hz, dc.filter_tau_ms)
            kg = int(round((seg.cue_s + 1.0) * dc.rate_hz)); m = min(len(X), len(Y)); pr = dec.predict(X[:m])[kg:]
            own = float(np.nanmax(ro._lagged(pr, Y[kg:m], max_lag)))
            oth = np.array([np.nanmax(ro._lagged(pr, F[kg:m], max_lag)) for F in foreign])
            rec["foreign"] = dict(own=own, foreign_mean=float(oth.mean()), foreign_p95=float(np.percentile(oth, 95)),
                                  p=float((1 + (oth >= own).sum()) / (1 + N_FOREIGN)))
        out.update(tag=job["tag"], seed=cfg.seed, ok=True)
        return out
    except Exception as ex:
        import traceback
        return dict(ok=False, tag=job["tag"], seed=job["cfg"]["seed"], error=f"{type(ex).__name__}: {ex}", trace=traceback.format_exc()[-900:])


def exp_recall_modes(cfg: Config, seeds, workers):
    """cue vs no_cue (spontaneous replay under noise) vs nm_pulse (a neuromodulator pulse, no input)."""
    out = C.results_dir("recall_modes")
    conds = {}
    for mode in ("cue", "no_cue", "nm_pulse"):
        c = cfg.model_copy(deep=True); c.protocol.recall_mode = mode; conds[mode] = c
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import get_context
    with ProcessPoolExecutor(max(workers, 1), mp_context=get_context("spawn")) as ex:
        runs = list(ex.map(_recall_modes_worker, C.jobs_for(conds, seeds, {"n": 1})))
    g = C.by_tag(runs)
    rep = ("## Recall modes -- partial cue vs spontaneous replay vs NM pulse (one stream)\n\n"
           "Uncued modes have no time reference, so the statistic that matters for them is the BEST-LAG r. It is tested two ways: "
           "against a circular shift of the true envelope (DEGENERATE for uncued modes -- the lag search spans the record, so the "
           "shifted copy is searched over the same alignments) and against 20 FOREIGN streams from the same generator "
           "(is recall closer to ITS stream than to others?), which is the test that can actually answer. `pattern r` asks the rate-pattern question "
           "instead: do the cells that fired during encoding fire during recall? Its baseline is the same correlation "
           "for the pre-encoding settle period.\n\n")
    summ = {}
    for mode, rs in g.items():
        rows = [("delay (sim s)", "recall E rate (Hz)", "spikes in window", "time-locked r (guarded)", "best-lag r", "shift-null 95th pct",
                 "shift p<0.05 (seeds)", "foreign-stream r (mean)", "own - foreign", "foreign p<0.05 (seeds)", "ordering rho", "pattern r", "ESN time-locked r")]
        summ[mode] = {}
        for k in range(len(rs[0]["recall"])):
            R = [r["recall"][k] for r in rs]
            v = dict(rate=C.ci95([x["rate_e_hz"] for x in R]), spikes=float(np.mean([x["n_spikes"] for x in R])),
                     locked=C.ci95([x["guarded_r"][0] for x in R]), best=C.ci95([x["bestlag"]["r"] for x in R]),
                     null95=C.ci95([x["bestlag"]["null_shift_p95"] for x in R]), n_sig=int(sum(x["bestlag"]["p"] < 0.05 for x in R)),
                     foreign=C.ci95([x["foreign"]["foreign_mean"] for x in R]), n_sig_f=int(sum(x["foreign"]["p"] < 0.05 for x in R)),
                     own_minus=C.paired_diff([x["foreign"]["own"] for x in R], [x["foreign"]["foreign_mean"] for x in R]),
                     ordering=C.ci95([x["ordering_rho"] for x in R]), pattern=C.ci95([x["pattern_r"] for x in R]),
                     esn=C.ci95([r["esn"]["recall"][k]["guarded_r"][0] for r in rs]))
            summ[mode][str(R[0]["delay_s"])] = v
            rows.append((R[0]["delay_s"], C.fmt(v["rate"]), f"{v['spikes']:.0f}", C.fmt(v["locked"]), C.fmt(v["best"]), C.fmt(v["null95"]),
                         f"{v['n_sig']}/{len(R)}", C.fmt(v["foreign"]), C.fmt(v["own_minus"]) + (" OWN WINS" if v["own_minus"]["beats"] else ""),
                         f"{v['n_sig_f']}/{len(R)}", C.fmt(v["ordering"]), C.fmt(v["pattern"]), C.fmt(v["esn"])))
        base = C.ci95([r["pattern_r_settle_baseline"] for r in rs])
        last = [r["recall"][-1] for r in rs]
        d_pat = C.paired_diff([x["pattern_r"] for x in last], [r["pattern_r_settle_baseline"] for r in rs])
        summ[mode]["pattern_vs_settle"] = d_pat
        expected = 0.05 * len(rs)
        rep += (f"### `{mode}`\n\n" + _table(rows) + f"\n- pattern r, settle baseline: {C.fmt(base)}; recall (last delay) - baseline: {C.fmt(d_pat)} -> "
                f"{'assembly REACTIVATES above baseline' if d_pat['beats'] else 'no reactivation above baseline'}\n"
                f"- best-lag seeds at p<0.05: expect ~{expected:.1f} of {len(rs)} by chance at each delay\n\n")
    C.save(out, cfg, runs, summ, rep)
    return out


# ------------------------------------------------------------------ recall-phase drive, candidate 1
DRIVE_STRENGTHS = (1.0, 2.0, 4.0)       # declared before any run; the WHOLE sweep is reported


def exp_recall_drive(cfg: Config, seeds, workers):
    """NM -> excitatory excitability (AHP block + threshold drop), without raising inhibition.

    SUCCESS CRITERION, fixed in advance: decoded recall matches its OWN stream better than 20 foreign streams
    (whole 95% CI of own - foreign above zero). Higher firing alone does not count.
    Conditions. Modes where NM is at reference during the probe (cue, no_cue) and the 1 s pulse (nm_pulse) are
    run with the drive off and on at strength 1. Modes where NM is ELEVATED for the whole probe (nm_sustained,
    cue_nm) carry the sweep, with the NM -> inhibitory-set-point coupling both on (the base model) and off
    (the drive as specified: excitability up, inhibition not raised)."""
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import get_context
    out = C.results_dir("recall_drive")

    def cond(mode, strength, inh_setpoint=True):
        c = cfg.model_copy(deep=True); c.protocol.recall_mode = mode
        c.mechanisms.nm_excitability = strength > 0; c.nm_excitability.strength = max(strength, 1.0) if strength > 0 else 1.0
        c.mechanisms.nm_inhibitory_setpoint = inh_setpoint
        return c
    conds = {}
    for mode in ("cue", "no_cue", "nm_pulse"):
        conds[f"{mode} | drive off"] = cond(mode, 0); conds[f"{mode} | drive x1"] = cond(mode, 1.0)
    for mode in ("nm_sustained", "cue_nm"):
        conds[f"{mode} | drive off"] = cond(mode, 0)
        conds[f"{mode} | drive off, NM-inh off"] = cond(mode, 0, False)
        conds[f"{mode} | drive x1"] = cond(mode, 1.0)
        for k in DRIVE_STRENGTHS:
            conds[f"{mode} | drive x{k:g}, NM-inh off"] = cond(mode, k, False)
    with ProcessPoolExecutor(max(workers, 1), mp_context=get_context("spawn")) as ex:
        runs = list(ex.map(_recall_modes_worker, C.jobs_for(conds, seeds, {"n": 1})))
    g = C.by_tag(runs)
    tri = lambda f: " / ".join(f(k) for k in range(len(next(iter(g.values()))[0]["recall"])))
    rows = [("condition", "recall E rate, Hz", "own - foreign best-lag r (SUCCESS if CI > 0)", "foreign-null p<0.05, seeds",
             "time-locked r (guarded)", "reactivation (pattern r)", "encode held-out r", "consolidation E rate, Hz")]
    summ, wins = {}, []
    for tag, rs in g.items():
        per = []
        for k in range(len(rs[0]["recall"])):
            R = [r["recall"][k] for r in rs]
            d = C.paired_diff([x["foreign"]["own"] for x in R], [x["foreign"]["foreign_mean"] for x in R])
            per.append(dict(delay_s=R[0]["delay_s"], rate=C.ci95([x["rate_e_hz"] for x in R]), own_minus_foreign=d,
                            n_sig=int(sum(x["foreign"]["p"] < 0.05 for x in R)), locked=C.ci95([x["guarded_r"][0] for x in R]),
                            pattern=C.ci95([x["pattern_r"] for x in R])))
            if d["beats"]:
                wins.append(f"{tag} @ {R[0]['delay_s']:g} s: {C.fmt(d)}")
        summ[tag] = dict(delays=per, encode=C.ci95([r["encode_heldout_r"][0] for r in rs]),
                         rate_consolidation=C.ci95([r.get("rate_e_consolidate_hz") for r in rs]))
        rows.append((tag, tri(lambda k: f"{per[k]['rate']['mean']:.3f}"),
                     tri(lambda k: f"{per[k]['own_minus_foreign']['mean']:+.3f} [{per[k]['own_minus_foreign']['lo']:+.3f}, {per[k]['own_minus_foreign']['hi']:+.3f}]"
                         + ("**" if per[k]["own_minus_foreign"]["beats"] else "")),
                     tri(lambda k: f"{per[k]['n_sig']}/{len(rs)}"), tri(lambda k: f"{per[k]['locked']['mean']:+.3f}"),
                     tri(lambda k: f"{per[k]['pattern']['mean']:+.3f}"), C.fmt(summ[tag]["encode"]), f"{summ[tag]['rate_consolidation']['mean']:.3f}"))
    n_tests = sum(len(v["delays"]) for v in summ.values())
    rep = ("## Recall-phase drive, candidate 1 -- NM raises excitatory excitability (AHP block + threshold drop)\n\n"
           "Basis: Bacon, Pickering & Mellor 2020 (doi:10.1093/cercor/bhaa159). Cells: three delays, `a / b / c`. "
           "**Success = own - foreign with its whole 95% CI above zero; higher firing alone does not count.**\n\n" + _table(rows) +
           f"\n### Verdict\n\n{len(wins)} of {n_tests} condition x delay cells meet the criterion"
           f" (about {0.025 * n_tests:.1f} expected by chance from one-sided 2.5% tails).\n" +
           ("".join(f"- {w}\n" for w in wins) if wins else "- none\n") +
           "\nThe drive strength was not tuned: x1 was fixed from one stated anchor before any run, and x2 / x4 are the declared sweep, reported whole.\n")
    C.save(out, cfg, runs, summ, rep)
    return out
