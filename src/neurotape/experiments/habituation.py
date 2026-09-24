"""Habituation as memory -- the minimal model, steps 1-3. Hypotheses and criteria: docs/habituation/PREREG.md.

  exp hab_memory     steps 1-2: does repetition alone (NM flat) store something stream-specific, and does it last?
                     arms none | std | std_presyn | std_hebb | hebb_only
  exp hab_salience   step 3: does salience fade with repetition when it is read off the habituating network
                     (network) and not when it is read off the raw input (raw)? And does storage follow it?
  exp hab_isi        Rankin characteristic 4: shorter inter-stimulus interval -> faster decrement

Every run is one seed = one network AND one stimulus family (a different stored sound, relatives and null
per seed). A failed seed is reported, never dropped. `--config` is a HabConfig YAML (configs/habituation*.yaml).
"""
from __future__ import annotations

import json
import os
import traceback
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path

import numpy as np
from scipy import stats

from . import common as C

# ------------------------------------------------------------------------------ arms
MEMORY_ARMS = {
    "none":       dict(depression=dict(on=False), longterm=dict(mode="off")),
    "std":        dict(depression=dict(on=True), longterm=dict(mode="off")),
    "std_presyn": dict(depression=dict(on=True), longterm=dict(mode="presynaptic")),
    "std_hebb":   dict(depression=dict(on=True), longterm=dict(mode="hebbian")),
    "hebb_only":  dict(depression=dict(on=False), longterm=dict(mode="hebbian")),
}
# step 3 runs on the step-2 substrate: two-timescale depression + anti-Hebbian long-term depression
SALIENCE_BASE = dict(depression=dict(on=True), longterm=dict(mode="hebbian"))
SALIENCE_ARMS = {
    "off":     dict(salience=dict(mode="off", eta_pot=0.0)),
    "raw":     dict(salience=dict(mode="raw", eta_pot=0.10)),
    "network": dict(salience=dict(mode="network", eta_pot=0.10)),
}


def _merge(base: dict, over: dict) -> dict:
    out = json.loads(json.dumps(base))
    for k, v in over.items():
        out[k] = _merge(out.get(k, {}), v) if isinstance(v, dict) else v
    return out


def _key(n, d, intf) -> str:
    return f"N{n}|d{d:g}|{'interf' if intf else 'silent'}"


# ------------------------------------------------------------------------------ worker: steps 1-2 (and 3's probes)
def _run_memory(job: dict) -> dict:
    try:
        from ..habituation import measure as M
        from ..habituation.config import HabConfig
        from ..habituation.protocol import calibrate_salience, make_sim
        from ..habituation.stimuli import family, louder

        cfg = HabConfig.model_validate(job["cfg"])
        p = cfg.protocol
        sim, st0 = make_sim(cfg)
        fam = family(cfg.seed, p.stim_s, p.n_novel, p.shifts_oct, n_interf=11)
        calib = fam.interference[8:]                       # never played as interference, never probed
        calibrate_salience(sim, st0, calib)
        base_db = cfg.periphery.level_db_spl
        salient = job.get("salient", False)
        lv = (lambda s: louder(s, p.salient_db, base_db)) if salient else (lambda s: s)
        stored = lv(fam.stored)
        rel_names = list(fam.relatives)
        probes = [stored] + [lv(fam.relatives[k]) for k in rel_names] + [lv(s) for s in fam.novel] + [fam.noise]
        i_nov = slice(1 + len(rel_names), 1 + len(rel_names) + len(fam.novel))
        i_noise = len(probes) - 1
        prng = np.random.default_rng(cfg.seed + 9001)
        rasters = np.stack([sim.raster(s, prng, p.probe_tail_s) for s in probes])
        stim_steps = int(round(p.stim_s / sim.dt))
        profiles = np.stack([sim.per.profile(s) for s in [stored] + [lv(s) for s in fam.novel]])
        n_cf = sim.per.cf.size
        delays = job.get("delays", p.delays_s)
        conds = [(d, False) for d in delays] + \
                ([(d, True) for d in delays if d >= p.interference_min_delay_s] if job.get("interference", True) else [])

        def seeds_for(d, intf):
            return 31 * int(d * 10) + (7 if intf else 3)

        def carry(state, d, intf):
            s = state.copy()
            sim.advance(s, d, np.random.default_rng(cfg.seed + seeds_for(d, intf)), fam.interference[:8] if intf else None)
            return s

        ctrl, ctrl_eff = {}, {}
        for d, intf in conds:
            s = carry(st0, d, intf)
            ctrl_eff[(d, intf)] = M.efficacy_by_cf(sim.net, s, n_cf)
            ctrl[(d, intf)] = M.summarise(sim.probe(s, rasters, cfg.seed + seeds_for(d, intf)), stim_steps)

        # ---- training: one sequence, snapshots right after the Nth presentation
        st = st0.copy()
        trng = np.random.default_rng(cfg.seed + 4242)
        reps, snaps = [], {}
        for rep in range(1, max(p.n_reps) + 1):
            rec = sim.present(st, stored, trng)
            reps.append(dict(rep=rep, R=float(rec.e_count.sum()), R_onset=float(rec.e_count[: max(stim_steps // 8, 1)].sum()),
                             nm_peak=float(rec.nm.max()), drive_peak=float(rec.drive.max()),
                             **M.channel_L(sim.net, st, profiles[0])))
            if rep in p.n_reps:
                snaps[rep] = st.copy()
            sim.quiet(st, p.isi_s - p.stim_s, trng)

        out = {}
        for n, snap in snaps.items():
            for d, intf in conds:
                s = carry(snap, d, intf)
                eff = M.efficacy_by_cf(sim.net, s, n_cf)
                tr = M.summarise(sim.probe(s, rasters, cfg.seed + seeds_for(d, intf)), stim_steps)
                c = ctrl[(d, intf)]
                S = M.suppression(tr["R"], c["R"])
                S_on = M.suppression(tr["R_onset"], c["R_onset"])
                S_nov = S[i_nov]
                rank, p_rank = M.rank_of_first(np.concatenate([[S[0]], S_nov]))
                eng = M.fingerprint_rank(1.0 - eff / ctrl_eff[(d, intf)], profiles)
                cp = M.cell_profile(sim.net, tr["cells"][i_noise], c["cells"][i_noise], sim.per.cf)
                beh = M.fingerprint_rank(cp, profiles)
                nm_st, nm_nov = float(tr["nm_peak"][0]), float(np.mean(tr["nm_peak"][i_nov]))
                out[_key(n, d, intf)] = dict(
                    N=n, delay_s=d, interference=intf,
                    S_stored=float(S[0]), S_novel_mean=float(np.nanmean(S_nov)), S_novel_sd=float(np.nanstd(S_nov)),
                    recog=float(S[0] - np.nanmean(S_nov)), rank=rank, p_rank=p_rank,
                    recog_onset=float(S_on[0] - np.nanmean(S_on[i_nov])),
                    relatives={k: float(S[1 + j] - np.nanmean(S_nov)) for j, k in enumerate(rel_names)},
                    S_noise=float(S[i_noise]),
                    engram_rank=eng[0], engram_p=eng[1], engram_r=eng[2],
                    afterimage_rank=beh[0], afterimage_p=beh[1], afterimage_r=beh[2],
                    nm_stored=nm_st, nm_novel=nm_nov, nm_stored_ctrl=float(c["nm_peak"][0]),
                    **M.channel_L(sim.net, s, profiles[0]))
        return dict(ok=True, tag=job["tag"], seed=cfg.seed, salient=salient, reps=reps, cells=out,
                    naive=dict(rate_e_spont_hz=sim.rate_e_spont, drive_ref=st0.drive_ref, k_nm=st0.k_nm,
                               R_ctrl_stored=float(ctrl[conds[0]]["R"][0]),
                               R_ctrl_novel_mean=float(np.mean(ctrl[conds[0]]["R"][i_nov])),
                               active_frac_stored=float((ctrl[conds[0]]["cells"][0] > 0).mean())))
    except Exception as e:
        return dict(ok=False, tag=job.get("tag"), seed=job["cfg"].get("seed"), error=f"{type(e).__name__}: {e}",
                    trace=traceback.format_exc()[-2000:])


# ------------------------------------------------------------------------------ worker: dishabituation (step 3)
def _run_dishab(job: dict) -> dict:
    """Habituate to the neutral stored sound (10 reps), then 5 cycles of [dishabituator -> stored] with 2
    re-habituating reps between cycles. The SAME loud dishabituator every cycle (Rankin: habituation of
    dishabituation). DI_c = R(stored after D_c) / R(stored, last habituating rep) - 1."""
    try:
        from ..habituation.config import HabConfig
        from ..habituation.protocol import calibrate_salience, make_sim
        from ..habituation.stimuli import family, louder
        cfg = HabConfig.model_validate(job["cfg"])
        p = cfg.protocol
        sim, st = make_sim(cfg)
        fam = family(cfg.seed, p.stim_s, p.n_novel, p.shifts_oct, n_interf=11)
        calibrate_salience(sim, st, fam.interference[8:])
        D = louder(fam.novel[0], p.salient_db, cfg.periphery.level_db_spl)
        rng = np.random.default_rng(cfg.seed + 777)
        gap = p.isi_s - p.stim_s

        def pres(spec):
            rec = sim.present(st, spec, rng)
            sim.quiet(st, gap, rng)
            return float(rec.e_count.sum()), float(rec.nm.max())

        hab = [pres(fam.stored) for _ in range(10)]
        cycles = []
        for c in range(5):
            last = pres(fam.stored) if c else hab[-1]
            rd, nmd = pres(D)
            rs, nms = pres(fam.stored)
            cycles.append(dict(cycle=c + 1, R_before=last[0], R_after=rs, DI=rs / last[0] - 1 if last[0] > 0 else float("nan"),
                               R_dishab=rd, nm_dishab=nmd, nm_stored_after=nms))
            pres(fam.stored)
        return dict(ok=True, tag=job["tag"], seed=cfg.seed, hab=hab, cycles=cycles)
    except Exception as e:
        return dict(ok=False, tag=job.get("tag"), seed=job["cfg"].get("seed"), error=f"{type(e).__name__}: {e}",
                    trace=traceback.format_exc()[-2000:])


# ------------------------------------------------------------------------------ plumbing
def _pool(fn, jobs, workers):
    os.environ.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", VECLIB_MAXIMUM_THREADS="1")
    if workers <= 1:
        return [fn(j) for j in jobs]
    with ProcessPoolExecutor(workers, mp_context=get_context("spawn")) as ex:
        return list(ex.map(fn, jobs))


def _hab_cfg(path):
    from ..habituation.config import load
    return load(path)


def _save(outdir: Path, cfg, runs, summary, report):
    from ..habituation.config import dump
    dump(cfg, outdir / "config.yaml")
    (outdir / "runs.json").write_text(json.dumps(runs, indent=1, default=float))
    (outdir / "summary.json").write_text(json.dumps(summary, indent=1, default=float))
    failed = [r for r in runs if not r.get("ok")]
    head = (f"# {outdir.name}\n\n_minimal habituation model: no time compression; delays are simulated seconds "
            f"(silences beyond {cfg.protocol.direct_silence_s:g} s are fast-forwarded in mean field)_\n\n")
    if failed:
        head += f"**{len(failed)} of {len(runs)} runs FAILED and are excluded:** " + \
                "; ".join(f"{r['tag']}/seed {r['seed']}: {r['error']}" for r in failed[:5]) + "\n\n"
    try:
        from ..monorepo import stamp
        (outdir / "provenance.json").write_text(json.dumps(stamp(["tools/result-provenance"]), indent=1, default=str))
    except Exception as e:
        head += f"_provenance stamp unavailable: {e}_\n\n"
    (outdir / "REPORT.md").write_text(head + report)


def _ci(v):
    return C.ci95(v)


def _f(c):
    return C.fmt(c)


def _cells(runs, tag):
    return [r for r in runs if r.get("ok") and r["tag"] == tag]


# ------------------------------------------------------------------------------ exp: steps 1-2
def exp_hab_memory(config_path, seeds, workers, arms=None) -> Path:
    base = _hab_cfg(config_path)
    arms = arms or list(MEMORY_ARMS)
    jobs = []
    for a in arms:
        cfg = _merge(base.model_dump(), MEMORY_ARMS[a])
        for s in seeds:
            jobs.append(dict(cfg={**cfg, "seed": int(s)}, tag=a))
    runs = _pool(_run_memory, jobs, workers)
    out = C.results_dir("hab_memory")
    summary, report = summarise_memory(runs, base, arms)
    _save(out, base, runs, summary, report)
    _figures_memory(out, runs, base, arms)
    return out


def summarise_memory(runs, base, arms, title="Steps 1-2: habituation as memory, NM held flat"):
    p = base.protocol
    n_null = p.n_novel
    summ, rep = {}, [f"## {title}\n"]
    rep.append(f"Each probe went to its own copy of the network; suppression S = 1 - R_trained/R_control against a "
               f"time-matched naive control given the identical input spikes and noise. Recognition = S(stored) - mean "
               f"S(novel), over a null of {n_null} novel sounds; 'top' = stored ranked above ALL of them "
               f"(p = 1/{n_null + 1}).\n")
    for a in arms:
        rs = _cells(runs, a)
        if not rs:
            rep.append(f"\n### {a}: no successful runs\n"); continue
        keys = list(rs[0]["cells"])
        summ[a] = {}
        rep.append(f"\n### arm `{a}` ({len(rs)} seeds)\n\n| N | delay | cond | recognition | top / seeds | S stored | "
                   f"reversed - null | shift 1/6 - null | shift 1/2 - null | engram rank (median) | afterimage rank (median) |"
                   f"\n|---|---|---|---|---|---|---|---|---|---|---|\n")
        for k in keys:
            cs = [r["cells"][k] for r in rs if k in r["cells"]]
            rc = _ci([c["recog"] for c in cs])
            top = sum(1 for c in cs if c["rank"] == 1)
            rel = {n: _ci([c["relatives"][n] for c in cs]) for n in cs[0]["relatives"]}
            ranks_e = [c["engram_rank"] for c in cs if c["engram_rank"] > 0]
            ranks_b = [c["afterimage_rank"] for c in cs if c["afterimage_rank"] > 0]
            summ[a][k] = dict(recog=rc, top=top, n=len(cs), relatives=rel, S_stored=_ci([c["S_stored"] for c in cs]),
                              engram_rank_median=float(np.median(ranks_e)) if ranks_e else None,
                              engram_top=sum(1 for x in ranks_e if x == 1),
                              afterimage_rank_median=float(np.median(ranks_b)) if ranks_b else None,
                              afterimage_top=sum(1 for x in ranks_b if x == 1),
                              L_stored=_ci([c.get("L_stored", np.nan) for c in cs]),
                              L_other=_ci([c.get("L_other", np.nan) for c in cs]))
            c0 = cs[0]
            relf = [f"{v['mean']:+.3f} [{v['lo']:+.3f},{v['hi']:+.3f}]" for v in rel.values()]
            rep.append(f"| {c0['N']} | {c0['delay_s']:g} s | {'interf' if c0['interference'] else 'silent'} | "
                       f"{rc['mean']:+.3f} [{rc['lo']:+.3f}, {rc['hi']:+.3f}] | {top}/{len(cs)} | "
                       f"{summ[a][k]['S_stored']['mean']:+.3f} | " + " | ".join(relf) + " | "
                       f"{summ[a][k]['engram_rank_median']} ({summ[a][k]['engram_top']} top) | "
                       f"{summ[a][k]['afterimage_rank_median']} ({summ[a][k]['afterimage_top']} top) |\n")
        # per-presentation decrement (Rankin 1)
        R = np.array([[x["R"] for x in r["reps"]] for r in rs])
        rho = [stats.spearmanr(np.arange(R.shape[1]), row)[0] for row in R]
        summ[a]["decrement"] = dict(R_mean=R.mean(0).tolist(), rho=rho, n_neg=int(sum(1 for x in rho if x < 0)))
        nv = [r["naive"] for r in rs]
        rep.append(f"\nNaive network: spontaneous E rate {np.mean([x['rate_e_spont_hz'] for x in nv]):.2f} Hz; "
                   f"response to the stored sound {np.mean([x['R_ctrl_stored'] for x in nv]):.0f} spikes "
                   f"(novel mean {np.mean([x['R_ctrl_novel_mean'] for x in nv]):.0f}); "
                   f"{100 * np.mean([x['active_frac_stored'] for x in nv]):.0f}% of E cells respond. "
                   f"Response across presentations 1..{R.shape[1]} (mean): "
                   + ", ".join(f"{v:.0f}" for v in R.mean(0)) +
                   f"; Spearman rho < 0 in {summ[a]['decrement']['n_neg']}/{len(rho)} seeds.\n")
    return summ, "".join(rep)


def _figures_memory(out, runs, base, arms):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    p = base.protocol
    fig, axs = plt.subplots(1, len(p.delays_s), figsize=(3.2 * len(p.delays_s), 3.2), sharey=True)
    for j, d in enumerate(p.delays_s):
        ax = axs[j] if len(p.delays_s) > 1 else axs
        for a in arms:
            rs = _cells(runs, a)
            if not rs:
                continue
            m, lo, hi = [], [], []
            for n in p.n_reps:
                c = _ci([r["cells"][_key(n, d, False)]["recog"] for r in rs])
                m.append(c["mean"]); lo.append(c["lo"]); hi.append(c["hi"])
            ax.errorbar(p.n_reps, m, yerr=[np.subtract(m, lo), np.subtract(hi, m)], label=a, capsize=2, marker="o", ms=3)
        ax.axhline(0, color="0.6", lw=0.6); ax.set_xscale("log", base=2); ax.set_title(f"delay {d:g} s (silent)", fontsize=9)
        ax.set_xlabel("presentations N")
    (axs[0] if len(p.delays_s) > 1 else axs).set_ylabel("recognition: S(stored) - mean S(novel)")
    (axs[-1] if len(p.delays_s) > 1 else axs).legend(fontsize=7)
    fig.text(0.5, 0.005, "minimal habituation model | 95% CI over seeds | no time compression", ha="center", fontsize=7, color="0.35")
    fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(out / "recognition.png", dpi=130); plt.close(fig)


# ------------------------------------------------------------------------------ exp: step 3
def exp_hab_salience(config_path, seeds, workers) -> Path:
    base = _hab_cfg(config_path)
    arms = [a for a in SALIENCE_ARMS if a != "off"]
    p = base.protocol
    delays = [d for d in p.delays_s if d >= 30.0]
    jobs, djobs = [], []
    for a in SALIENCE_ARMS:
        cfg = _merge(_merge(base.model_dump(), SALIENCE_BASE), SALIENCE_ARMS[a])
        for s in seeds:
            djobs.append(dict(cfg={**cfg, "seed": int(s)}, tag=a))
            if a == "off":
                continue
            for sal in (True, False):
                jobs.append(dict(cfg={**cfg, "seed": int(s)}, tag=f"{a}|{'salient' if sal else 'neutral'}",
                                 salient=sal, delays=delays, interference=False))
    runs = _pool(_run_memory, jobs, workers)
    druns = _pool(_run_dishab, djobs, workers)
    out = C.results_dir("hab_salience")
    summary, report = summarise_salience(runs, druns, base, arms, delays)
    _save(out, base, runs + druns, summary, report)
    _figures_salience(out, runs, druns, arms)
    return out


def summarise_salience(runs, druns, base, arms, delays):
    p = base.protocol
    summ, rep = {"presentations": {}, "probes": {}, "dishabituation": {}}, [
        "## Step 3: does salience fade with repetition, and does storage follow it?\n\n"
        "`raw`: NM driven by the unadapted input. `network`: NM driven by the E population's own (habituating) "
        "response. NM raises input gain and gates potentiation of active synapses (dual-process: habituation + "
        "sensitisation). Training sound: `salient` = the stored sound "
        f"+{p.salient_db:g} dB; `neutral` = at the base level.\n"]
    for a in arms:
        for kind in ("salient", "neutral"):
            tag = f"{a}|{kind}"
            rs = _cells(runs, tag)
            if not rs:
                rep.append(f"\n### {tag}: no successful runs\n"); continue
            nm = np.array([[x["nm_peak"] for x in r["reps"]] for r in rs])
            R = np.array([[x["R"] for x in r["reps"]] for r in rs])
            Ls = np.array([[x.get("L_stored", np.nan) for x in r["reps"]] for r in rs])
            last = nm.shape[1] - 1
            ix = sorted({i - 1 for i in (1, 2, 4, 8, last + 1) if i <= last + 1})
            lab = ", ".join(str(i + 1) for i in ix)
            d_nm = _ci(nm[:, last] - nm[:, 0])
            ratio = _ci(nm[:, last] / np.maximum(nm[:, 0], 1e-9))
            summ["presentations"][tag] = dict(nm_mean=nm.mean(0).tolist(), R_mean=R.mean(0).tolist(),
                                              L_stored_mean=np.nanmean(Ls, 0).tolist(), d_nm=d_nm, nm_ratio=ratio)
            rep.append(f"\n### `{tag}` ({len(rs)} seeds)\n\n"
                       f"- NM peak, presentation 1 -> {last + 1}: " + " ".join(f"{v:.3f}" for v in nm.mean(0)[ix]) +
                       f" (presentations {lab}); last - first {_f(d_nm)}; last / first {_f(ratio)}\n"
                       f"- response (E spikes): " + " ".join(f"{v:.0f}" for v in R.mean(0)[ix]) + "\n"
                       f"- L on the stored sound's channels after each: " + " ".join(f"{v:.3f}" for v in np.nanmean(Ls, 0)[ix]) +
                       " (1 = naive; >1 potentiated, <1 depressed)\n\n| N | delay | recognition | NM(stored probe) | NM(novel probes) | NM stored - novel | L stored |\n|---|---|---|---|---|---|---|\n")
            summ["probes"][tag] = {}
            for n in p.n_reps:
                for d in delays:
                    k = _key(n, d, False)
                    cs = [r["cells"][k] for r in rs]
                    rc = _ci([c["recog"] for c in cs])
                    dn = _ci([c["nm_stored"] - c["nm_novel"] for c in cs])
                    summ["probes"][tag][k] = dict(recog=rc, nm_diff=dn, nm_stored=_ci([c["nm_stored"] for c in cs]),
                                                  nm_novel=_ci([c["nm_novel"] for c in cs]), L_stored=_ci([c.get("L_stored", np.nan) for c in cs]))
                    rep.append(f"| {n} | {d:g} s | {rc['mean']:+.3f} [{rc['lo']:+.3f}, {rc['hi']:+.3f}] | "
                               f"{np.mean([c['nm_stored'] for c in cs]):.3f} | {np.mean([c['nm_novel'] for c in cs]):.3f} | "
                               f"{dn['mean']:+.3f} [{dn['lo']:+.3f}, {dn['hi']:+.3f}] | "
                               f"{np.nanmean([c.get('L_stored', np.nan) for c in cs]):.3f} |\n")
    rep.append("\n## Dishabituation, and whether it habituates (Rankin characteristics 8 and 9)\n\n"
               "10 presentations of the neutral stored sound, then 5 cycles of [the same loud dishabituator -> the stored "
               "sound]. DI = response after the dishabituator / response before it - 1.\n\n"
               "| arm | DI cycle 1 | DI cycle 5 | DI5 - DI1 | NM to dishabituator 1 -> 5 |\n|---|---|---|---|---|\n")
    for a in SALIENCE_ARMS:
        rs = [r for r in druns if r.get("ok") and r["tag"] == a]
        if not rs:
            continue
        DI = np.array([[c["DI"] for c in r["cycles"]] for r in rs])
        nmd = np.array([[c["nm_dishab"] for c in r["cycles"]] for r in rs])
        d15 = _ci(DI[:, -1] - DI[:, 0])
        summ["dishabituation"][a] = dict(DI_mean=np.nanmean(DI, 0).tolist(), d15=d15, nm_dishab_mean=nmd.mean(0).tolist(),
                                         DI1=_ci(DI[:, 0]), DI5=_ci(DI[:, -1]))
        rep.append(f"| `{a}` | {_f(_ci(DI[:, 0]))} | {_f(_ci(DI[:, -1]))} | {_f(d15)} | "
                   f"{nmd.mean(0)[0]:.3f} -> {nmd.mean(0)[-1]:.3f} |\n")
    return summ, "".join(rep)


def _figures_salience(out, runs, druns, arms):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.2))
    for a in arms:
        for kind, ls in (("salient", "-"), ("neutral", "--")):
            rs = _cells(runs, f"{a}|{kind}")
            if not rs:
                continue
            nm = np.array([[x["nm_peak"] for x in r["reps"]] for r in rs])
            Ls = np.array([[x.get("L_stored", np.nan) for x in r["reps"]] for r in rs])
            R = np.array([[x["R"] for x in r["reps"]] for r in rs])
            x = np.arange(1, nm.shape[1] + 1)
            axs[0].plot(x, nm.mean(0), ls, label=f"{a} {kind}")
            axs[1].plot(x, R.mean(0), ls, label=f"{a} {kind}")
            axs[2].plot(x, np.nanmean(Ls, 0), ls, label=f"{a} {kind}")
    axs[0].set_ylabel("NM peak"); axs[1].set_ylabel("response (E spikes)"); axs[2].set_ylabel("L, stored channels")
    for ax in axs:
        ax.set_xlabel("presentation")
    axs[0].legend(fontsize=7)
    fig.text(0.5, 0.005, "minimal habituation model | means over seeds", ha="center", fontsize=7, color="0.35")
    fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(out / "salience.png", dpi=130); plt.close(fig)


# ------------------------------------------------------------------------------ exp: Rankin 4
def exp_hab_isi(config_path, seeds, workers) -> Path:
    base = _hab_cfg(config_path)
    jobs = []
    for isi in (base.protocol.stim_s + 0.5, base.protocol.isi_s, 8.0):
        cfg = _merge(base.model_dump(), dict(MEMORY_ARMS["std_hebb"], protocol=dict(isi_s=isi, delays_s=[2.0, 30.0])))
        for s in seeds:
            jobs.append(dict(cfg={**cfg, "seed": int(s)}, tag=f"isi{isi:g}", interference=False))
    runs = _pool(_run_memory, jobs, workers)
    out = C.results_dir("hab_isi")
    rep = ["## Rankin characteristic 4: inter-stimulus interval\n\n| ISI | response, presentation 1 | last presentation | "
           "last / first | recognition N=max, 2 s | recognition N=max, 30 s |\n|---|---|---|---|---|---|\n"]
    summ = {}
    for tag in sorted({j["tag"] for j in jobs}, key=lambda t: float(t[3:])):
        rs = _cells(runs, tag)
        if not rs:
            continue
        R = np.array([[x["R"] for x in r["reps"]] for r in rs])
        ratio = _ci(R[:, -1] / np.maximum(R[:, 0], 1))
        nmax = max(base.protocol.n_reps)
        r2 = _ci([r["cells"][_key(nmax, 2.0, False)]["recog"] for r in rs])
        r30 = _ci([r["cells"][_key(nmax, 30.0, False)]["recog"] for r in rs])
        summ[tag] = dict(ratio=ratio, recog2=r2, recog30=r30)
        rep.append(f"| {tag[3:]} s | {R[:, 0].mean():.0f} | {R[:, -1].mean():.0f} | {_f(ratio)} | {_f(r2)} | {_f(r30)} |\n")
    _save(out, base, runs, summ, "".join(rep))
    return out
