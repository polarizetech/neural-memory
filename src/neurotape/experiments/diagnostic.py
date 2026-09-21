"""Storage diagnostic (D2 + D3): does encoding write anything STREAM-SPECIFIC into the weights?

recall_drive returned 0 of 18, and its frozen-weights control showed recall-phase reactivation is the same
with plasticity on or off. So before any scale-up: is there a trace in the weights at all?

Per seed (same seeds and stimuli as recall_drive's drive-off cue condition; 200 E / 50 I; quick.yaml):
  plastic       the real run, drive off, ONE recall probe after the 120 s consolidation interval so the
                post-consolidation snapshot precedes every recall cue. Encoding is identical to the baseline.
  plastic_off   null (b): the same run with plasticity off -- dW must be ~0.
  frozen x 21   plasticity frozen, from the pre-encoding weights, on the stored stream and on the SAME 20 foreign
                streams used as the recall null. Each is a REPLICATE: identical wiring, but a different membrane-
                noise stream and different auditory-nerve spikes than the plastic run -- otherwise the stored stream
                would win by sharing the plastic run's noise realisation rather than by its stimulus.
From each frozen run's E-cell activity the dW it WOULD have written is predicted with the network's own equations
(recall/storage.py:predict_dw) and correlated with the observed dW over the synapses that exist.

PRE-REGISTERED PASS (fixed before any run): on TOTAL dW at the pre-first-recall snapshot, the stored stream ranks
1st of 21 in >= 7/10 seeds AND its correlation exceeds the 95th percentile of the >= 1000-shuffle permutation null
in >= 7/10 seeds. Early-phase and late-phase dW, and the end-of-encoding snapshot, are reported beside it and
do not enter the criterion. Anything else is a FAIL, reported with the per-seed numbers.
"""
from __future__ import annotations

import json

import numpy as np

from ..config import Config
from . import common as C

N_FOREIGN, REPLICATE, CONSOLIDATE_S, N_PERM = 20, 1_000_000, 120.0, 1000
COMPONENTS = ("early", "late", "total")


def _job_cfg(cfg: Config, seed: int, kind: str) -> Config:
    c = cfg.model_copy(deep=True); c.seed = seed; c.protocol.recall_mode = "cue"
    if kind.startswith("frozen"):
        c.mechanisms.plasticity = False; c.sim.replicate_offset = REPLICATE; c.sim.log_cat = True
        c.protocol.recall_mode = "no_cue"; c.protocol.recall_delays_s = [0.5]; c.protocol.recall_s = 0.5     # encoding is all that is needed
    else:
        c.protocol.recall_delays_s = [CONSOLIDATE_S]; c.sim.snapshot_weights = True; c.sim.log_cat = True
        c.mechanisms.plasticity = kind == "plastic"
    return c


def _worker(job):
    try:
        from ..network import build_inputs, simulate
        from ..frontend.io import synthetic_streams
        from ..recall import storage as S
        cfg = Config.model_validate(job["cfg"]); kind = job["kind"]; seed = cfg.seed
        k = int(kind.split("_")[1]) if kind.startswith("frozen") else 0
        stream_seed = seed if k == 0 else 10_000 + seed * 100 + (k - 1)          # k = 0 is the STORED stream
        inputs = build_inputs(synthetic_streams(1, cfg.protocol.encode_s, seed=stream_seed), cfg); res = simulate(cfg, inputs)
        enc = res.timeline.segment("encode"); i, t = res.spikes_e
        horizons = {"post_encode": enc.dur, "pre_first_recall": enc.dur + CONSOLIDATE_S}
        nm_v = res.nm.nm.copy(); nm_v[res.nm.t >= enc.t1] = cfg.neuromod.consolidation_tonic       # frozen runs stop early; consolidation NM is tonic
        cat_t, cat_v = res.extra["CaT"]
        pred = S.predict_dw(i, t, res.syn_i, res.syn_j, res.n_exc, cfg, res.nm.t, nm_v, cat_t, cat_v, enc.t0, enc.t1, horizons)
        out = dict(ok=True, seed=seed, kind=kind, syn_sig=int(res.syn_i.sum() * 7 + res.syn_j.sum()),
                   rate_e_encode_hz=float(((t >= enc.t0) & (t < enc.t1)).sum() / res.n_exc / enc.dur),
                   pred={h: (p[0].astype(np.float32), p[1].astype(np.float32)) for h, p in pred.items()})
        if not kind.startswith("frozen"):
            out["mag"] = {h: S.magnitudes(res, cfg, after=h) for h in horizons}
            out["obs"] = {}
            h0, z0 = S.snapshot(res, "pre_encode")
            for h in horizons:
                h1, z1 = S.snapshot(res, h); out["obs"][h] = ((h1 - h0).astype(np.float32), (z1 - z0).astype(np.float32))
        return out
    except Exception as ex:
        import traceback
        return dict(ok=False, seed=job["cfg"]["seed"], kind=job["kind"], error=f"{type(ex).__name__}: {ex}", trace=traceback.format_exc()[-900:])


def _parts(pair):
    e, l = np.asarray(pair[0], float), np.asarray(pair[1], float)
    return dict(early=e, late=l, total=e + l)


def exp_storage_diagnostic(cfg: Config, seeds, workers):
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import get_context
    from ..recall import storage as S
    out = C.results_dir("storage_diagnostic")
    kinds = ["plastic", "plastic_off"] + [f"frozen_{k}" for k in range(N_FOREIGN + 1)]
    jobs = [dict(cfg=_job_cfg(cfg, int(s), k).model_dump(), kind=k) for s in seeds for k in kinds]
    with ProcessPoolExecutor(max(workers, 1), mp_context=get_context("spawn")) as ex:
        runs = list(ex.map(_worker, jobs))
    bad = [r for r in runs if not r.get("ok")]
    by = {(r["seed"], r["kind"]): r for r in runs if r.get("ok")}
    per_seed, keep = [], {}
    for s in seeds:
        s = int(s); pl, off = by.get((s, "plastic")), by.get((s, "plastic_off"))
        fro = [by.get((s, f"frozen_{k}")) for k in range(N_FOREIGN + 1)]
        if pl is None or off is None or any(f is None for f in fro):
            per_seed.append(dict(seed=s, complete=False)); continue
        assert all(f["syn_sig"] == pl["syn_sig"] for f in fro), "a replicate was wired differently from the plastic run"
        row = dict(seed=s, complete=True, mag=pl["mag"], rate_plastic=pl["rate_e_encode_hz"], rate_frozen_stored=fro[0]["rate_e_encode_hz"], decode={}, self_r={}, null_b={})
        for h in ("post_encode", "pre_first_recall"):
            obs, own = _parts(pl["obs"][h]), _parts(pl["pred"][h]); offp = _parts(off["obs"][h])
            row["null_b"][h] = {c: float(np.abs(offp[c]).max()) for c in COMPONENTS}
            row["decode"][h], row["self_r"][h] = {}, {}
            for c in COMPONENTS:
                row["self_r"][h][c] = S.corr(obs[c], own[c])        # predictor fed the plastic run's OWN activity: its ceiling
                row["decode"][h][c] = S.stream_decode(obs[c], [_parts(f["pred"][h])[c] for f in fro], n_perm=N_PERM, seed=s)
        per_seed.append(row); keep[s] = dict(obs=pl["obs"], pred_stored=fro[0]["pred"])
    done = [r for r in per_seed if r.get("complete")]
    P = lambda r: r["decode"]["pre_first_recall"]["total"]
    n_rank1 = sum(1 for r in done if P(r).get("defined") and P(r)["rank"] == 1)
    n_perm = sum(1 for r in done if P(r).get("defined") and P(r)["beats_perm95"])
    passed = len(done) >= 10 and n_rank1 >= 7 and n_perm >= 7
    fmt = lambda d: "undefined (no variance)" if not d.get("defined") else f"rank {d['rank']}/21, r {d['r_stored']:+.3f} (foreign max {d['r_foreign_max']:+.3f}, perm95 {d['perm_p95']:+.3f}{', beats' if d['beats_perm95'] else ''})"
    rep = ("## Storage diagnostic -- is anything stream-specific written into the weights?\n\n200 E / 50 I, quick.yaml, drive off, the recall_drive baseline "
           f"seeds and stimuli. {len(done)} of {len(list(seeds))} seeds complete; {len(bad)} of {len(runs)} runs failed.\n\n### D2 -- dW magnitudes (units of the baseline weight h_0), "
           "pre-encoding -> immediately before the first recall cue (120 s = 2 h of slow-process time)\n\n"
           "| seed | synapses | frac changed: early / late / total | mean abs dW: early / late / total | max abs dW: early / late / total | tagged (potentiated) | late-phase | cells with protein | null (b) max abs dW, plasticity off |\n|---|---|---|---|---|---|---|---|---|\n")
    for r in done:
        m = r["mag"]["pre_first_recall"]; tri = lambda key, f: " / ".join(f.format(m[c][key]) for c in COMPONENTS)
        rep += (f"| {r['seed']} | {m['n_synapses']} | {tri('frac_changed', '{:.3f}')} | {tri('mean_abs', '{:.4f}')} | {tri('max_abs', '{:.3f}')} | "
                f"{m['n_tagged']} ({m['n_tagged_potentiated']}) | {m['n_late_phase']} | {m['n_cells_protein']} | {max(r['null_b']['pre_first_recall'].values()):.2e} |\n")
    rep += "\nAt the END OF ENCODING (before consolidation):\n\n| seed | frac changed (early) | mean abs early dW | max abs early dW | tagged (potentiated) |\n|---|---|---|---|---|\n"
    for r in done:
        m = r["mag"]["post_encode"]; rep += f"| {r['seed']} | {m['early']['frac_changed']:.3f} | {m['early']['mean_abs']:.4f} | {m['early']['max_abs']:.3f} | {m['n_tagged']} ({m['n_tagged_potentiated']}) |\n"
    rep += ("\n### D3 -- stream decode: rank of the STORED stream among 21 (chance = 1/21), at the pre-first-recall snapshot\n\n"
            "| seed | TOTAL dW (the pre-registered test) | early-phase dW | late-phase dW | predictor ceiling r (own activity): early / late / total |\n|---|---|---|---|---|\n")
    for r in done:
        d = r["decode"]["pre_first_recall"]; sr = r["self_r"]["pre_first_recall"]
        rep += f"| {r['seed']} | {fmt(d['total'])} | {fmt(d['early'])} | {fmt(d['late'])} | " + " / ".join(f"{sr[c]:+.3f}" for c in COMPONENTS) + " |\n"
    rep += "\nAt the end of encoding (early-phase dW only is meaningful there):\n\n| seed | early-phase dW |\n|---|---|\n"
    for r in done:
        rep += f"| {r['seed']} | {fmt(r['decode']['post_encode']['early'])} |\n"
    rep += (f"\n### Verdict against the pre-registered criterion (total dW, pre-first-recall)\n\n- stored stream ranks 1st: **{n_rank1} of {len(done)}** seeds (needed >= 7)\n"
            f"- stored-stream correlation above the permutation 95th percentile: **{n_perm} of {len(done)}** seeds (needed >= 7)\n- **{'PASS' if passed else 'FAIL'}**\n")
    if bad:
        rep += "\nFailed runs: " + "; ".join(f"seed {b['seed']} {b['kind']}: {b['error']}" for b in bad[:6]) + "\n"
    slim = [{k: v for k, v in r.items() if k not in ("pred", "obs")} for r in runs]
    summary = dict(per_seed=per_seed, n_rank1=n_rank1, n_beats_perm=n_perm, n_complete=len(done), passed=bool(passed))
    C.save(out, cfg, slim, summary, rep)
    np.savez_compressed(out / "dw_arrays.npz", **{f"seed{s}_{h}_{w}_{c}": _parts(v[w][h])[c].astype(np.float32)
                                                   for s, v in keep.items() for h in ("post_encode", "pre_first_recall") for w in ("obs", "pred_stored") for c in COMPONENTS})
    return out
