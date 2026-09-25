"""E01-stentor-map -- the pre-registered analysis. Reads outputs/<part>/runs.json, writes outputs/summary.json and
prints the criteria table. Frozen with PREREG.md by the -prereg tag; every rule here is stated in PREREG.md section 3.

    .venv/bin/python experiments/E01-stentor-map/analyse.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import yaml
from scipy import stats

HERE = Path(__file__).resolve().parent


def ci(v) -> dict:
    v = np.asarray([x for x in v if x is not None and np.isfinite(x)], float)
    if v.size < 2:
        return dict(mean=float(v.mean()) if v.size else float("nan"), lo=float("nan"), hi=float("nan"), n=int(v.size))
    h = stats.t.ppf(0.975, v.size - 1) * v.std(ddof=1) / np.sqrt(v.size)
    return dict(mean=float(v.mean()), lo=float(v.mean() - h), hi=float(v.mean() + h), n=int(v.size))


def runs(part):
    f = HERE / "outputs" / part / "runs.json"
    return json.loads(f.read_text()) if f.exists() else []


def slope(rates, D):
    x, y = np.log10(rates), 20 * np.log10(D)
    return float(np.polyfit(x, y, 1)[0])


def main():
    c = yaml.safe_load((HERE / "config.yaml").read_text())
    out = {"failed_runs": [], "criteria": {}}
    # ---------------------------------------------------------------- SR1
    r1 = [r for r in runs("sr1") if r.get("ok")]
    out["failed_runs"] += [(r["part"], r["arm"], r["seed"], r["error"]) for r in runs("sr1") if not r.get("ok")]
    sr1 = {}
    for arm in ("std", "hebb_only", "none"):
        rs = [r for r in r1 if r["arm"] == arm]
        if not rs:
            continue
        by = {}
        for r in rs:
            for x in r["results"]:
                by.setdefault(x["scale"], []).append(x)
        sr1[arm] = {str(sc): dict(D16=ci([x["D16"] for x in xs]),
                                   half_median=float(np.median([x["half"] or 99 for x in xs])),
                                   half_abs_median=float(np.median([x["half_abs"] or 99 for x in xs])),
                                   retention=ci([x["retention"] for x in xs if not x["floor"]]),
                                   recognition=ci([x["recognition"] for x in xs if not x["floor"]]),
                                   floor_seeds=sum(x["floor"] for x in xs), n=len(xs),
                                   R_mean=np.mean([x["R"] for x in xs], 0).tolist())
                     for sc, xs in sorted(by.items(), key=lambda kv: -kv[0])}
        if arm == "hebb_only":
            base = {r["seed"]: next(x for x in r["results"] if x["scale"] == 1.0)["D16"] for r in rs}
            for sc in c["sr1"]["recovery_scales"][1:]:
                d = [next(x for x in r["results"] if x["scale"] == sc)["D16"] - base[r["seed"]] for r in rs]
                sr1[arm][str(sc)]["D16_minus_x1"] = ci(d)
    out["sr1"] = sr1
    scales = [str(s) for s in c["sr1"]["recovery_scales"]]
    if "std" in sr1:
        m = [sr1["std"][s]["D16"]["mean"] for s in scales]
        h = [sr1["std"][s]["half_median"] for s in scales]
        deepen = all(b > a for a, b in zip(m, m[1:]))
        later = all(b >= a for a, b in zip(h, h[1:])) and h[-1] > h[0]
        out["criteria"]["SR1-std"] = dict(D16_means=m, half_medians=h, deepens_monotone=deepen, half_later_monotone=later,
                                          verdict="PASS" if deepen and later else "FAIL")
    if "hebb_only" in sr1:
        ok_d = all(sr1["hebb_only"][s]["D16_minus_x1"]["lo"] <= 0 <= sr1["hebb_only"][s]["D16_minus_x1"]["hi"]
                   and abs(sr1["hebb_only"][s]["D16_minus_x1"]["mean"]) < 0.05 for s in scales[1:])
        ok_h = len({sr1["hebb_only"][s]["half_median"] for s in scales}) == 1
        out["criteria"]["SR1-hebb_only"] = dict(null_D16=ok_d, null_half=ok_h, verdict="PASS" if ok_d and ok_h else "FAIL")
    # ---------------------------------------------------------------- SR2 (measurement only)
    r2 = [r for r in runs("sr2") if r.get("ok")]
    out["failed_runs"] += [(r["part"], r["arm"], r["seed"], r["error"]) for r in runs("sr2") if not r.get("ok")]
    p2, sr2 = c["sr2"], {}
    rng = np.random.default_rng(p2["bootstrap"]["seed"])
    for arm in ("std", "hebb_only", "none"):
        for sched in p2["schedules"]:
            rs = [r for r in r2 if r["arm"] == arm]
            if not rs:
                continue
            Dmat = np.array([[next(x["D"] for x in r["results"] if x["schedule"] == sched and x["rate_hz"] == f)
                              for f in p2["rates_hz"]] for r in rs], float)
            meanD = np.nanmean(Dmat, 0)
            res = dict(rates=p2["rates_hz"], D_mean=meanD.tolist(), D_ci=[ci(Dmat[:, j]) for j in range(Dmat.shape[1])])
            for name, (lo, hi) in (("primary", p2["fit_primary_hz"]), ("secondary", p2["fit_secondary_hz"])):
                idx = [j for j, f in enumerate(p2["rates_hz"]) if lo <= f <= hi and f not in p2["excluded_from_fit_hz"]]
                rr = np.array(p2["rates_hz"])[idx]
                if np.all(meanD[idx] > 0):
                    s = slope(rr, meanD[idx])
                    boots = []
                    for _ in range(p2["bootstrap"]["n"]):
                        bm = np.nanmean(Dmat[rng.integers(0, len(rs), len(rs))][:, idx], 0)
                        if np.all(bm > 0):
                            boots.append(slope(rr, bm))
                    res[name] = dict(range_hz=[lo, hi], slope_db_per_decade=s, stages=s / 20.0,
                                     ci95=[float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))] if boots else None,
                                     boot_valid=len(boots))
                else:
                    res[name] = dict(range_hz=[lo, hi], slope_db_per_decade=None,
                                     note="a mean decrement <= 0 in the window: 20 log10 D undefined")
            sr2[f"{arm}|{sched}"] = res
    out["sr2"] = sr2
    # ---------------------------------------------------------------- SR3
    r3 = [r for r in runs("sr3") if r.get("ok")]
    out["failed_runs"] += [(r["part"], r["arm"], r["seed"], r["error"]) for r in runs("sr3") if not r.get("ok")]
    sr3 = {}
    for arm in ("std", "hebb_only", "none"):
        rs = [r for r in r3 if r["arm"] == arm]
        if not rs:
            continue
        sr3[arm] = {k: ci([r["effect"][k] for r in rs]) for k in ("plus10", "plus20", "gap")}
    out["sr3"] = sr3
    for arm in ("std", "hebb_only"):
        if arm in sr3:
            ok = {k: sr3[arm][k]["hi"] < 0 for k in ("plus10", "plus20")}
            out["criteria"][f"SR3-{arm}"] = dict(**{f"deepens_{k}": v for k, v in ok.items()},
                                                effect_plus10=sr3[arm]["plus10"], effect_plus20=sr3[arm]["plus20"],
                                                verdict="PASS" if all(ok.values()) else "FAIL")
    (HERE / "outputs" / "summary.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out["criteria"], indent=1, default=float))


if __name__ == "__main__":
    main()
