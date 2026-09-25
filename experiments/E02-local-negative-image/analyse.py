"""E02 frozen analysis. Reads outputs/{control,main,sensitivity}/runs.json and predictions/predictions.json; writes
outputs/analysis.json and prints the criteria table. Every threshold is read from config.yaml or PREREG.md
section 3 as written there; nothing here is chosen after seeing output.

Statistics (PREREG section 3):
  * all comparisons are PAIRED over seeds (same network, stimulus family, relay rasters and noise seeds);
  * mean and two-sided t intervals over seeds: 95 % for "exceeds", 90 % for TOST equivalence;
  * paired MDE from the plasticity-off arm Z: (t_{1-a/2,n-1} + t_{power,n-1}) * sd / sqrt(n);
  * verdict rules:
      exceeds X   PASS if the 95 % CI lower bound > X;
                  FAIL if the 90 % CI lies inside +/- sesoi (an equivalence NULL) and MDE <= sesoi;
                  otherwise UNINTERPRETABLE.
      within      PASS if the 90 % CI lies inside +/- sesoi (TOST);
                  FAIL if the whole 95 % CI lies outside +/- sesoi;
                  otherwise UNINTERPRETABLE.

    .venv/bin/python experiments/E02-local-negative-image/analyse.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import yaml
from scipy import stats

HERE = Path(__file__).resolve().parent
C = yaml.safe_load((HERE / "config.yaml").read_text())
AN = C["analysis"]
SESOI = AN["sesoi"]
PROBES = ["A", "full", "partial", "none"]
DELAYS = C["delays_s"]


def load(stage):
    p = HERE / "outputs" / stage / "runs.json"
    return json.loads(p.read_text()) if p.exists() else []


def ci(x, level):
    x = np.asarray([v for v in x if np.isfinite(v)], float)
    n = x.size
    if n < 3:
        return dict(n=int(n), mean=float(np.mean(x)) if n else float("nan"), lo=float("nan"), hi=float("nan"))
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(n)
    t = stats.t.ppf(0.5 + level / 2, n - 1)
    return dict(n=int(n), mean=float(m), lo=float(m - t * se), hi=float(m + t * se), sd=float(x.std(ddof=1)))


def mde(sd, n):
    return float((stats.t.ppf(1 - AN["alpha"] / 2, n - 1) + stats.t.ppf(AN["power"], n - 1)) * sd / np.sqrt(n))


def verdict_exceeds(x, thr, mde_val):
    c95, c90 = ci(x, 0.95), ci(x, 0.90)
    if c95["lo"] > thr:
        v = "PASS"
    elif -SESOI < c90["lo"] and c90["hi"] < SESOI and mde_val <= SESOI:
        v = "FAIL"
    else:
        v = "UNINTERPRETABLE"
    return dict(verdict=v, ci95=c95, ci90=c90, threshold=thr, mde=mde_val)


def verdict_within(x, mde_val):
    c95, c90 = ci(x, 0.95), ci(x, 0.90)
    if -SESOI < c90["lo"] and c90["hi"] < SESOI:
        v = "PASS"
    elif c95["lo"] > SESOI or c95["hi"] < -SESOI:
        v = "FAIL"
    else:
        v = "UNINTERPRETABLE"
    return dict(verdict=v, ci95=c95, ci90=c90, bound=SESOI, mde=mde_val)


# ------------------------------------------------------------------------------------------------ per-run quantities
def row(run, d):
    return next(r for r in run["probes"] if r["delay_s"] == d)


def S(r, p, which="on"):
    c = r[f"ctl_{which}"][p]
    return 1 - r[f"tr_{which}"][p] / c if c > 0 else float("nan")


def SR(r, p):
    return S(r, "A") - S(r, p)


def rev(r, p):
    """Trained-specific disinhibition of probe p by removal: (tr_off - tr_on)/ctl_on - (ctl_off - ctl_on)/ctl_on."""
    c = r["ctl_on"][p]
    if c <= 0:
        return float("nan")
    return (r["tr_off"][p] - r["tr_on"][p]) / c - (r["ctl_off"][p] - r["ctl_on"][p]) / c


def naive_rev(r, p):
    c = r["ctl_on"][p]
    return (r["ctl_off"][p] - r["ctl_on"][p]) / c if c > 0 else float("nan")


def index(runs):
    """(arm, variant, schedule) -> {seed: run}; failed runs listed separately, never dropped silently."""
    ix, failed = {}, []
    for r in runs:
        if not r["ok"]:
            failed.append({k: r[k] for k in ("arm", "variant", "schedule", "seed", "error")})
            continue
        ix.setdefault((r["arm"], r["variant"], r["schedule"]), {})[r["seed"]] = r
    return ix, failed


def paired(ix, key_a, key_b, fn):
    """fn(run_a, run_b) over seeds present in both."""
    a, b = ix.get(key_a, {}), ix.get(key_b, {})
    return [fn(a[s], b[s]) for s in sorted(set(a) & set(b))]


def first_k(R, k):
    return float(np.mean(R[:k]))


def half_point(R, k):
    R = np.asarray(R, float)
    R1 = R[:k].mean()
    if not R1 > R[-1]:
        return None
    thr = R1 - 0.5 * (R1 - R[-1])
    return next(i + 1 for i, v in enumerate(R) if v <= thr)


def angle(u, v):
    nu, nv = np.linalg.norm(u), np.linalg.norm(v)
    if nu == 0 or nv == 0:
        return float("nan")
    return float(np.degrees(np.arccos(np.clip(u @ v / (nu * nv), -1, 1))))


def axis_readout(run, which, rng):
    """Within = last n - first n of block 1; across = first n of block 3 - first n of block 1 (per cell).
    Null: the 3n trials' labels permuted, AXIS_PERMS times. Spaced schedule only (blocks exist)."""
    n = AN["axis_first_n"]
    X = np.asarray(run[f"{which}_cells"], float)           # (60, NE)
    b1, b1_last, b3 = X[:n], X[20 - n:20], X[40:40 + n]
    obs = angle(b1_last.mean(0) - b1.mean(0), b3.mean(0) - b1.mean(0))
    pool = np.concatenate([b1, b1_last, b3])
    null = []
    for _ in range(AN["axis_null_perms"]):
        q = pool[rng.permutation(3 * n)]
        null.append(angle(q[n:2 * n].mean(0) - q[:n].mean(0), q[2 * n:].mean(0) - q[:n].mean(0)))
    null = np.asarray([v for v in null if np.isfinite(v)])
    pct = float((null < obs).mean()) if null.size and np.isfinite(obs) else float("nan")
    return dict(angle=obs, null_median=float(np.median(null)) if null.size else float("nan"), percentile=pct)


# ------------------------------------------------------------------------------------------------ analysis
def main():
    ctl_runs, main_runs, sens_runs = load("control"), load("main"), load("sensitivity")
    if not ctl_runs:
        sys.exit("outputs/control/runs.json missing: the control stage runs first")
    ix, failed = index(ctl_runs + main_runs)
    sx, sfailed = index(sens_runs)
    pred = json.loads((HERE / "predictions/predictions.json").read_text())["summary"]
    out = dict(failed=failed + sfailed, criteria={}, measurements={})
    Cr, Me = out["criteria"], out["measurements"]

    # ---- MDE from the plasticity-off pairing (Z), per schedule x delay x probe; the MAX is the design's MDE
    mdes = {}
    for sched in C["schedules"]:
        Z = ix.get(("Z", "base", sched), {})
        for d in DELAYS:
            for p in AN["map_probes"]:
                x = np.array([SR(row(r, d), p) for r in Z.values()], float)
                x = x[np.isfinite(x)]
                if x.size >= 3:
                    mdes[f"{sched}/{d}/{p}"] = mde(x.std(ddof=1), x.size)
    MDE = max(mdes.values()) if mdes else float("nan")
    Me["mde_cells"], Me["mde_design"] = mdes, MDE

    # ---- P1: Arm A failure map (primary, measurement plus bound)
    amap = {}
    for sched in C["schedules"]:
        A = ix.get(("A", "base", sched), {})
        for p in AN["map_probes"]:
            cells = []
            for d in DELAYS:
                c = ci([SR(row(r, d), p) for r in A.values()], 0.95)
                cells.append(dict(delay_s=d, **c))
            obs_b = max([c["delay_s"] for c in cells if c["lo"] > SESOI], default=None)
            pred_b = pred["arms"]["A"][sched]["boundary_delay_s"][p]
            ok = (obs_b is None and pred_b is None) or (obs_b is not None and pred_b is not None and
                                                         abs(DELAYS.index(obs_b) - DELAYS.index(pred_b)) <= 1)
            amap[f"{sched}/{p}"] = dict(cells=cells, observed_boundary_s=obs_b, predicted_boundary_s=pred_b,
                                        verdict="PASS" if ok else "FAIL")
    Cr["P1_A_map"] = amap

    # ---- P2: B-vs-H removal (discriminating)
    ref = AN["removal_reference_probe"]
    for sched in C["schedules"]:
        for d in AN["removal_delays_s"]:
            k = f"{sched}/{d}"
            both = paired(ix, ("B", "base", sched), ("A", "base", sched),      # seeds present in BOTH arms
                          lambda b, a: (S(row(b, d), "A") - S(row(a, d), "A"),
                                        rev(row(b, d), "A") - rev(row(b, d), ref)))
            lc = [x[0] for x in both]
            sri_b = [rev(row(r, d), "A") - rev(row(r, d), ref) for r in ix.get(("B", "base", sched), {}).values()]
            reversal_vs_half_lc = [x[1] - 0.5 * x[0] for x in both]
            lc_v = verdict_exceeds(lc, SESOI, MDE)
            b_v = verdict_exceeds(reversal_vs_half_lc, 0.0, MDE)
            if lc_v["verdict"] != "PASS":
                b_v = dict(b_v, verdict="UNINTERPRETABLE", why="no learned component above SESOI to reverse")
            sri_h = [rev(row(r, d), "A") - rev(row(r, d), ref) for r in ix.get(("H", "base", sched), {}).values()]
            Cr[f"P2a_learned_component/{k}"] = lc_v
            Cr[f"P2b_B_removal_reverses/{k}"] = b_v
            Cr[f"P2c_H_removal_null/{k}"] = verdict_within(sri_h, MDE)
            Me[f"removal_reversal/{k}"] = dict(B=ci(sri_b, 0.95), H=ci(sri_h, 0.95))

    # ---- P3: naive removal is not stimulus-specific (Z controls, every delay pooled per schedule at the first delay)
    for sched in C["schedules"]:
        Z = ix.get(("Z", "base", sched), {})
        x = [naive_rev(row(r, DELAYS[0]), "A") - naive_rev(row(r, DELAYS[0]), ref) for r in Z.values()]
        Cr[f"P3_naive_removal_unspecific/{sched}"] = verdict_within(x, MDE)
        Me[f"naive_removal_effect/{sched}"] = dict(A=ci([naive_rev(row(r, DELAYS[0]), "A") for r in Z.values()], 0.95))

    # ---- P4: Arm R (Stentor structure): synthesis block 0 vs 1, massed schedule for acquisition
    k1 = AN["first_k"]
    for sched in C["schedules"]:
        a, b = ("R", "syn0.00", sched), ("R", "syn1.00", sched)
        dD = paired(ix, a, b, lambda x, y: (1 - np.mean(x["R_train"][-AN["last_k"]:]) / first_k(x["R_train"], k1)) -
                    (1 - np.mean(y["R_train"][-AN["last_k"]:]) / first_k(y["R_train"], k1)))
        dh = paired(ix, a, b, lambda x, y: (half_point(y["R_train"], k1) or 99) - (half_point(x["R_train"], k1) or 99))
        if sched == "massed":                                   # spaced dD includes 2 h of baseline drain: report only
            Cr[f"P4a_block_deepens_decrement/{sched}"] = verdict_exceeds(dD, SESOI, MDE)
        else:
            Me[f"R_decrement_block_minus_none/{sched}"] = ci(dD, 0.95)
        Me[f"R_half_point_earlier_by/{sched}"] = ci(dh, 0.95)
        for d in AN["r_retention_delays_s"]:
            ret = paired(ix, a, b, lambda x, y: S(row(x, d), "A") - S(row(y, d), "A"))
            base = paired(ix, a, b, lambda x, y: row(x, d)["ctl_on"]["A"] / row(y, d)["ctl_on"]["A"] - 1
                          if row(y, d)["ctl_on"]["A"] > 0 else float("nan"))
            Cr[f"P4b_block_prolongs_retention/{sched}/{d}"] = verdict_exceeds(ret, SESOI, MDE)
            Cr[f"P4c_untrained_baseline_holds/{sched}/{d}"] = verdict_within(base, MDE)

    # ---- P5: massed vs spaced, per arm (direction pre-registered in PREREG section 2)
    for arm, var in [("A", "base"), ("H", "base"), ("B", "base"), ("R", "syn1.00"), ("Z", "base")]:
        for d in (300, 1800, 3600):
            x = paired(ix, (arm, var, "spaced"), (arm, var, "massed"), lambda s, m: S(row(s, d), "A") - S(row(m, d), "A"))
            Me[f"spaced_minus_massed/{arm}/{d}"] = dict(ci95=ci(x, 0.95), ci90=ci(x, 0.90))

    # ---- P6: global-gain positive control (the readout must see global as global)
    for sched in C["schedules"]:
        G = ix.get(("G", "base", sched), {})
        d = AN["removal_delays_s"][0]
        Cr[f"P6a_gain_suppresses/{sched}"] = verdict_exceeds([S(row(r, d), "A") for r in G.values()], SESOI, MDE)
        Cr[f"P6b_gain_unspecific/{sched}"] = verdict_within([SR(row(r, d), ref) for r in G.values()], MDE)

    # ---- axis readout (measurement), spaced schedule only
    rng = np.random.default_rng(AN["bootstrap"]["seed"])
    axis = {}
    for (arm, var, sched), runs in sorted(ix.items()):
        if sched != "spaced":
            continue
        for which in ("onset", "sust"):
            res = [axis_readout(r, which, rng) for r in runs.values()]
            ang = [x["angle"] for x in res]
            pct = np.array([x["percentile"] for x in res], float)
            axis[f"{arm}/{var}/{which}"] = dict(angle=ci(ang, 0.95),
                                                null_median=float(np.nanmedian([x["null_median"] for x in res])),
                                                n_aligned=int((pct < 0.025).sum()), n_anti=int((pct > 0.975).sum()),
                                                n=len(res))
    Me["axis"] = axis

    # ---- sensitivity: does any headline verdict's point estimate cross its threshold? (5 seeds; direction only)
    sens = {}
    for (arm, var, sched), runs in sx.items():
        d = AN["removal_delays_s"][0]
        if arm in ("B", "H"):
            x = [rev(row(r, d), "A") - rev(row(r, d), ref) for r in runs.values()]
        else:
            dd = AN["r_retention_delays_s"][-1]
            x = [S(row(r, dd), "A") for r in runs.values()]
        sens[f"{arm}/{var}/{sched}"] = ci(x, 0.95)
    Me["sensitivity"] = sens

    (HERE / "outputs" / "analysis.json").write_text(json.dumps(out, indent=1, default=float))
    print(f"design MDE (max over Z cells) = {MDE:.4f}  SESOI = {SESOI}")
    for k, v in Cr.items():
        if "verdict" in v:
            m = v.get("ci95", {}).get("mean", float("nan"))
            print(f"{k:<52} {v['verdict']:<16} mean {m:+.4f}")
        else:
            for kk, vv in v.items():
                print(f"{k + '/' + kk:<52} {vv['verdict']:<16} observed {vv['observed_boundary_s']}  predicted {vv['predicted_boundary_s']}")
    print(f"failed runs: {len(out['failed'])}")


if __name__ == "__main__":
    main()
