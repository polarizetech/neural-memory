"""Storage diagnostic, second pass: a FROZEN-ACTIVITY BANK, the residual decode (P0), and the rerun under a
calibrated rule with and without plastic input synapses (P3).

With plasticity off a network's activity does not depend on the plasticity parameters or on `input_plastic`, so the
21 frozen replicate runs per seed are made ONCE and their activity saved; every condition's dW prediction is then
computed offline from that bank under that condition's rule. (D4 discarded its 20 foreign predictions, which is why
P0 could not be done from saved data; the bank is bit-reproducible, so regenerating it changes nothing.)

Replicates: identical wiring, different membrane noise and different auditory-nerve spikes than the plastic run.
PASS criterion, unchanged: on total dW at the pre-first-recall snapshot the stored stream ranks 1st of 21 in
>= 7/10 seeds AND beats the 95th percentile of a 1000-shuffle permutation null in >= 7/10. For condition B the
test is on ALL plastic weights concatenated (E->E + input->E); each projection is reported beside it.
"""
from __future__ import annotations

import numpy as np

from ..config import Config
from . import common as C
from .diagnostic import CONSOLIDATE_S, N_FOREIGN, N_PERM, REPLICATE, _job_cfg

BANK = C.ROOT / "results" / "frozen_bank"
COMPONENTS = ("early", "late", "total")


def _bank_worker(job):
    try:
        from ..network import build_inputs, simulate
        from ..frontend.io import synthetic_streams
        cfg = Config.model_validate(job["cfg"]); seed, k = cfg.seed, job["k"]
        path = BANK / f"s{seed}_k{k}.npz"
        if path.exists():
            return dict(ok=True, seed=seed, k=k, cached=True)
        stream_seed = seed if k == 0 else 10_000 + seed * 100 + (k - 1)
        inputs = build_inputs(synthetic_streams(1, cfg.protocol.encode_s, seed=stream_seed), cfg); res = simulate(cfg, inputs)
        enc = res.timeline.segment("encode"); cat_t, cat_v = res.extra["CaT"]; ie = res.extra["in_e"]; si = inputs.spikes_enc
        nm_v = res.nm.nm.copy(); nm_v[res.nm.t >= enc.t1] = cfg.neuromod.consolidation_tonic
        BANK.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, e_i=res.spikes_e[0].astype(np.uint16), e_t=res.spikes_e[1].astype(np.float32), cat_t0=float(cat_t[0]),
                            cat=cat_v.astype(np.float32), in_i=si.i.astype(np.uint16), in_t=(si.t + enc.t0).astype(np.float32), n_in=si.n,
                            syn_i=res.syn_i, syn_j=res.syn_j, ine_i=ie[0], ine_j=ie[1], nm_t=res.nm.t, nm_v=nm_v, enc=np.array([enc.t0, enc.t1]))
        return dict(ok=True, seed=seed, k=k, cached=False)
    except Exception as ex:
        import traceback
        return dict(ok=False, seed=job["cfg"]["seed"], k=job["k"], error=f"{type(ex).__name__}: {ex}", trace=traceback.format_exc()[-700:])


def build_bank(cfg: Config, seeds, workers):
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import get_context
    jobs = [dict(cfg=_job_cfg(cfg, int(s), f"frozen_{k}").model_dump(), k=k) for s in seeds for k in range(N_FOREIGN + 1)]
    with ProcessPoolExecutor(max(workers, 1), mp_context=get_context("spawn")) as ex:
        return list(ex.map(_bank_worker, jobs))


def _predict_worker(job):
    """One (seed, stream): the dW this stream's frozen activity would have written under `cfg`'s rule."""
    from ..recall import storage as S
    cfg = Config.model_validate(job["cfg"]); b = np.load(BANK / f"s{job['seed']}_k{job['k']}.npz")
    enc0, enc1 = b["enc"]; hz = {"post_encode": float(enc1 - enc0), "pre_first_recall": float(enc1 - enc0) + CONSOLIDATE_S}
    cat_t = b["cat_t0"] + np.arange(b["cat"].shape[1]) * 1e-3
    extra = [dict(pre_i=b["in_i"].astype(int), pre_t=b["in_t"].astype(float), n_pre=int(b["n_in"]), syn_i=b["ine_i"], syn_j=b["ine_j"])] if job["joint"] else []
    pred = S.predict_dw(b["e_i"].astype(int), b["e_t"].astype(float), b["syn_i"], b["syn_j"], cfg.network.n_exc, cfg, b["nm_t"], b["nm_v"],
                        cat_t, b["cat"], float(enc0), float(enc1), hz, extra_projections=extra)
    if not job["joint"]:
        pred = {h: [v] for h, v in pred.items()}
    return job["seed"], job["k"], {h: [(e.astype(np.float32), l.astype(np.float32)) for e, l in v] for h, v in pred.items()}


def predictions(cfg: Config, seeds, workers, joint: bool) -> dict:
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import get_context
    jobs = [dict(cfg=cfg.model_dump(), seed=int(s), k=k, joint=joint) for s in seeds for k in range(N_FOREIGN + 1)]
    with ProcessPoolExecutor(max(workers, 1), mp_context=get_context("spawn")) as ex:
        return {(s, k): p for s, k, p in ex.map(_predict_worker, jobs)}


def _vec(parts, comp):
    """parts: [(early, late), ...] per projection -> one concatenated vector for the component."""
    pick = {"early": lambda e, l: e, "late": lambda e, l: l, "total": lambda e, l: e + l}[comp]
    return np.concatenate([np.asarray(pick(np.asarray(e, float), np.asarray(l, float))) for e, l in parts])


def decode_table(obs: dict, preds: dict, seeds, projections=("all",)) -> list[dict]:
    """obs[seed][horizon] = [(early, late) per projection]; preds[(seed, k)][horizon] likewise."""
    from ..recall import storage as S
    rows = []
    for s in map(int, seeds):
        row = dict(seed=s)
        for hz in ("post_encode", "pre_first_recall"):
            for name in projections:
                sel = (lambda parts: parts) if name == "all" else (lambda parts, n=name: [parts[{"ee": 0, "in": 1}[n]]])
                for comp in COMPONENTS:
                    o = _vec(sel(obs[s][hz]), comp); P = [_vec(sel(preds[(s, k)][hz]), comp) for k in range(N_FOREIGN + 1)]
                    for mode in ("raw", "residual"):
                        row[f"{hz}|{name}|{comp}|{mode}"] = S.stream_decode(o, P, n_perm=N_PERM, seed=s, residual=(mode == "residual"))
        rows.append(row)
    return rows


def fmt_cell(d) -> str:
    return "undefined" if not d.get("defined") else f"{d['rank']} (r {d['r_stored']:+.3f}, best foreign {d['r_foreign_max']:+.3f}{', >p95' if d['beats_perm95'] else ''})"


def rank_table(rows, key_prefix: str, mode: str) -> tuple[str, dict]:
    txt = f"| seed | total | early | late |\n|---|---|---|---|\n"; stats = {}
    for r in rows:
        txt += f"| {r['seed']} | " + " | ".join(fmt_cell(r[f"{key_prefix}|{c}|{mode}"]) for c in ("total", "early", "late")) + " |\n"
    for c in ("total", "early", "late"):
        d = [r[f"{key_prefix}|{c}|{mode}"] for r in rows]; ok = [x for x in d if x.get("defined")]
        stats[c] = dict(n_rank1=sum(x["rank"] == 1 for x in ok), n_perm=sum(x["beats_perm95"] for x in ok), mean_rank=float(np.mean([x["rank"] for x in ok])) if ok else float("nan"), n=len(ok))
    txt += "| | " + " | ".join(f"1st in **{stats[c]['n_rank1']}/{stats[c]['n']}**, mean rank {stats[c]['mean_rank']:.1f}, >p95 in {stats[c]['n_perm']}/{stats[c]['n']}" for c in ("total", "early", "late")) + " |\n"
    return txt, stats


# ---------------------------------------------------------------------------------------------------------- P0
def exp_residual_decode(cfg: Config, seeds, workers):
    """P0: D4's OBSERVED dW (unchanged, from its saved arrays) against 21 predictions under the CURRENT rule."""
    import glob
    out = C.results_dir("residual_decode"); bank = build_bank(cfg, seeds, workers)
    src = sorted(glob.glob(str(C.ROOT / "results" / "*storage_diagnostic" / "dw_arrays.npz")))[0]; z = np.load(src)
    obs = {int(s): {h: [(z[f"seed{int(s)}_{h}_obs_early"], z[f"seed{int(s)}_{h}_obs_late"])] for h in ("post_encode", "pre_first_recall")} for s in seeds}
    rows = decode_table(obs, predictions(cfg, seeds, workers, joint=False), seeds)
    raw_t, raw_s = rank_table(rows, "pre_first_recall|all", "raw"); res_t, res_s = rank_table(rows, "pre_first_recall|all", "residual")
    passed = res_s["total"]["n_rank1"] >= 7
    rep = ("## P0 -- residual decode of the D4 data\n\nObserved dW: D4's own saved arrays, untouched. Predictions: the frozen-activity bank, current rule. Cells: rank of the stored stream "
           "among 21 (r stored, best foreign; '>p95' = above the permutation 95th percentile).\n\n### Raw decode (reproduces D4)\n\n" + raw_t +
           "\n### RESIDUAL decode -- the mean of the 21 predictions removed from the observed dW and from every prediction\n\n" + res_t +
           f"\n**Pre-registered pass (stored stream 1st in >= 7/10 seeds, total dW): {'PASS' if passed else 'FAIL'}** -- {res_s['total']['n_rank1']}/10.\n")
    C.save(out, cfg, [dict(ok=b.get("ok"), seed=b.get("seed"), tag=f"bank_k{b.get('k')}", error=b.get("error")) for b in bank], dict(rows=rows, raw=raw_s, residual=res_s, passed=bool(passed)), rep)
    return out


# ---------------------------------------------------------------------------------------------------------- P3
def _plastic_worker(job):
    try:
        from ..network import build_inputs, simulate
        from ..frontend.io import synthetic_streams
        from ..recall import storage as S
        cfg = Config.model_validate(job["cfg"]); seed = cfg.seed
        inputs = build_inputs(synthetic_streams(1, cfg.protocol.encode_s, seed=seed), cfg); res = simulate(cfg, inputs)
        projs = ["ee"] + (["in"] if cfg.mechanisms.input_plastic else [])
        enc = res.timeline.segment("encode"); t = res.spikes_e[1]
        out = dict(ok=True, seed=seed, kind=job["kind"], rate_e_encode_hz=float(((t >= enc.t0) & (t < enc.t1)).sum() / res.n_exc / enc.dur), mag={}, obs={})
        for hz in ("post_encode", "pre_first_recall"):
            out["mag"][hz] = {pj: S.magnitudes(res, cfg, after=hz, projection=pj) for pj in projs}
            out["obs"][hz] = []
            for pj in projs:
                h0, z0 = S.snapshot(res, "pre_encode", pj); h1, z1 = S.snapshot(res, hz, pj)
                out["obs"][hz].append(((h1 - h0).astype(np.float32), (z1 - z0).astype(np.float32)))
        return out
    except Exception as ex:
        import traceback
        return dict(ok=False, seed=job["cfg"]["seed"], kind=job["kind"], error=f"{type(ex).__name__}: {ex}", trace=traceback.format_exc()[-800:])


def _condition(cfg: Config, seeds, workers, name: str, input_plastic: bool):
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import get_context
    out = C.results_dir(f"storage_{name}")
    rule = cfg.model_copy(deep=True); rule.plasticity = type(rule.plasticity)(preset="gb2012_hippocampal_cal"); rule.mechanisms.input_plastic = input_plastic
    bank = build_bank(cfg, seeds, workers)                    # cached; frozen activity does not depend on the rule
    jobs = []
    for s in seeds:
        for kind in ("plastic", "plastic_off"):
            c = _job_cfg(rule, int(s), kind); c.sim.log_cat = False
            jobs.append(dict(cfg=c.model_dump(), kind=kind))
    with ProcessPoolExecutor(max(workers, 1), mp_context=get_context("spawn")) as ex:
        runs = list(ex.map(_plastic_worker, jobs))
    by = {(r["seed"], r["kind"]): r for r in runs if r.get("ok")}; done = [int(s) for s in seeds if (int(s), "plastic") in by and (int(s), "plastic_off") in by]
    preds = predictions(rule, done, workers, joint=input_plastic)
    obs = {s: by[(s, "plastic")]["obs"] for s in done}
    projections = ("all", "ee", "in") if input_plastic else ("all",)
    rows = decode_table(obs, preds, done, projections=projections)
    rep = (f"## Storage diagnostic, condition {name} -- calibrated rule (Graupner & Brunel 2012 hippocampal, theta_p 1.18), input->E "
           f"{'PLASTIC' if input_plastic else 'fixed'}\n\n200 E / 50 I, quick.yaml, drive off, seeds and stimuli as D4. {len(done)} of {len(list(seeds))} seeds complete; "
           f"{sum(not r.get('ok') for r in runs)} of {len(runs)} plastic/null runs failed.\n")
    for pj in (["ee", "in"] if input_plastic else ["ee"]):
        rep += (f"\n### Tags and magnitudes -- {'E->E' if pj == 'ee' else 'input->E'} (units of h_0)\n\n| seed | synapses | END OF ENCODING tags: potentiation / depression | AFTER CONSOLIDATION tags: pot / dep | late-phase: pot / dep | "
                "frac changed (early / late) | mean abs dW (early / late / total) | max abs dW total | null (b) max abs dW, plasticity off | E rate encode Hz |\n|---|---|---|---|---|---|---|---|---|---|\n")
        for s in done:
            a, b = by[(s, "plastic")]["mag"]["post_encode"][pj], by[(s, "plastic")]["mag"]["pre_first_recall"][pj]
            k = 0 if pj == "ee" else 1; nb = max(float(np.abs(e).max() + np.abs(l).max()) for e, l in [by[(s, "plastic_off")]["obs"]["pre_first_recall"][k]])
            rep += (f"| {s} | {b['n_synapses']} | {a['n_tagged_potentiated']} / {a['n_tagged_depressed']} | {b['n_tagged_potentiated']} / {b['n_tagged_depressed']} | "
                    f"{b['n_late_potentiated']} / {b['n_late_depressed']} | {b['early']['frac_changed']:.3f} / {b['late']['frac_changed']:.3f} | "
                    f"{b['early']['mean_abs']:.4f} / {b['late']['mean_abs']:.4f} / {b['total']['mean_abs']:.4f} | {b['total']['max_abs']:.3f} | {nb:.1e} | {by[(s, 'plastic')]['rate_e_encode_hz']:.2f} |\n")
    stats = {}
    for pj in projections:
        label = {"all": "ALL plastic weights (the pre-registered test)" if input_plastic else "E->E (all plastic weights; the pre-registered test)", "ee": "E->E only", "in": "input->E only"}[pj]
        for mode in ("raw", "residual"):
            t, st = rank_table(rows, f"pre_first_recall|{pj}", mode); stats[f"{pj}|{mode}"] = st
            rep += f"\n### Stream decode, {label} -- {mode.upper()} -- rank of the stored stream among 21\n\n" + t
    st = stats["all|raw"]["total"]; passed = st["n"] >= 10 and st["n_rank1"] >= 7 and st["n_perm"] >= 7
    sr = stats["all|residual"]["total"]
    rep += (f"\n### Verdict (total dW, all plastic weights, pre-first-recall)\n\n- RAW: 1st in **{st['n_rank1']}/{st['n']}**, above permutation p95 in **{st['n_perm']}/{st['n']}** -> **{'PASS' if passed else 'FAIL'}**\n"
            f"- RESIDUAL: 1st in **{sr['n_rank1']}/{sr['n']}**, above permutation p95 in **{sr['n_perm']}/{sr['n']}** -> **{'PASS' if (sr['n_rank1'] >= 7 and sr['n_perm'] >= 7) else 'FAIL'}**\n")
    slim = [{k: v for k, v in r.items() if k != "obs"} for r in runs]
    C.save(out, rule, slim, dict(stats=stats, passed_raw=bool(passed), rows=rows), rep)
    return out


def exp_storage_A(cfg, seeds, workers):
    return _condition(cfg, seeds, workers, "A", input_plastic=False)


def exp_storage_B(cfg, seeds, workers):
    return _condition(cfg, seeds, workers, "B", input_plastic=True)
