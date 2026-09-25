"""E03-synthesis-block -- scores outputs/ against PREREG.md section 3. Reads only; writes outputs/analysis.json.

    .venv/bin/python experiments/E03-synthesis-block/analyse.py

Criteria per arm (thresholds in config.yaml `criteria`, verbatim from PREREG section 3):
  C0 gate       R1-R8 all pass with the block off
  C1 baseline   untrained |p_block - p_ctrl| <= tol at every untrained tap (180 min level 3 and 4; 720, 810 min level 4)
  C2 accel      in each short protocol, mean p over training taps: block - control <= -margin
  C3 time0      long protocol, first test tap (2 min): |block - control| <= tol
  C4 retention  long protocol, block - control <= -margin at >= min_count of the retention delays
  C5 recovery   long protocol, control at 90 min >= fraction x untrained control at 810 min
An arm PASSES if C0-C5 all pass. A value within 1e-3 of its threshold is flagged `at_threshold`.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
EPS = 1e-3


def load(stage: str) -> list[dict]:
    return json.loads((HERE / "outputs" / stage / "runs.json").read_text())


def index(runs):
    ix = {}
    for r in runs:
        ix[(r["setting"], r["arm"], r["protocol"], r["block"])] = r
    return ix


def score_arm(c, ix, setting, arm, gate=None) -> dict:
    cr = c["criteria"]
    g = lambda p, b: ix[(setting, arm, p, b)]  # noqa: E731
    out, flags = {}, []

    def near(v, thr):
        if abs(v - thr) < EPS:
            flags.append(thr)

    if gate is not None:
        out["C0"] = dict(pass_=all(v["ok"] for v in gate.values()), failed=[k for k, v in gate.items() if not v["ok"]])
    # C1
    diffs = {}
    for p in ("untrained_short", "untrained_long"):
        ub, uc = g(p, True)["untrained"], g(p, False)["untrained"]
        for k in uc:
            diffs[f"{p}:{k}"] = ub[k] - uc[k]
    worst = max(diffs.values(), key=abs)
    near(abs(worst), cr["baseline_tol"])
    out["C1"] = dict(pass_=all(abs(v) <= cr["baseline_tol"] for v in diffs.values()), diffs=diffs)
    # C2
    acc = {}
    for p in ("puro_short", "chx_short", "puro_short_15"):
        n = g(p, False)["n_train"]
        mc = sum(g(p, False)["p"][:n]) / n
        mb = sum(g(p, True)["p"][:n]) / n
        acc[p] = dict(control=mc, block=mb, diff=mb - mc, final_control=g(p, False)["p"][n - 1],
                      final_block=g(p, True)["p"][n - 1])
        near(mb - mc, -cr["accel_margin"])
    out["C2"] = dict(pass_=all(v["diff"] <= -cr["accel_margin"] for v in acc.values()), protocols=acc)
    # C3-C5 from the long protocol
    lc, lb = g("long", False), g("long", True)
    n = lc["n_train"]
    delays = c["protocols"]["long"]["test_after_min"]
    tc = dict(zip(delays, lc["p"][n:]))
    tb = dict(zip(delays, lb["p"][n:]))
    d0 = tb[delays[0]] - tc[delays[0]]
    near(abs(d0), cr["time0_tol"])
    out["C3"] = dict(pass_=abs(d0) <= cr["time0_tol"], control=tc[delays[0]], block=tb[delays[0]], diff=d0)
    ret = {d: tb[d] - tc[d] for d in cr["retention_delays"]}
    for v in ret.values():
        near(v, -cr["retention_margin"])
    k = sum(v <= -cr["retention_margin"] for v in ret.values())
    out["C4"] = dict(pass_=k >= cr["retention_min_count"], diffs=ret, count=k, test_control=tc, test_block=tb,
                     end_of_training=dict(control=lc["p"][n - 1], block=lb["p"][n - 1]))
    naive = g("untrained_long", False)["untrained"]["level4@810"]
    near(tc[90], cr["recovery_fraction"] * naive)
    out["C5"] = dict(pass_=tc[90] >= cr["recovery_fraction"] * naive, control_90=tc[90], untrained_810=naive)
    keys = ["C0", "C1", "C2", "C3", "C4", "C5"] if gate is not None else ["C1", "C2", "C3", "C4", "C5"]
    out["pass"] = all(out[k]["pass_"] for k in keys)
    out["at_threshold"] = bool(flags)
    return out


def main():
    c = yaml.safe_load((HERE / "config.yaml").read_text())
    runs = load("main")
    failed = [r for r in runs if not r["ok"]]
    gate = {r["arm"]: r["gate"] for r in json.loads((HERE / "outputs" / "main" / "gate.json").read_text()) if r["ok"]}
    ix = index(r for r in runs if r["ok"])
    arms = sorted({r["arm"] for r in runs})
    res = dict(failed_runs=len(failed), main={}, sensitivity={})
    for a in arms:
        try:
            res["main"][a] = score_arm(c, ix, "main", a, gate.get(a))
        except KeyError as e:
            res["main"][a] = dict(pass_=None, error=f"missing run {e}")
    sp = HERE / "outputs" / "sensitivity" / "runs.json"
    if sp.exists():
        sruns = load("sensitivity")
        res["failed_runs"] += sum(not r["ok"] for r in sruns)
        six = index(r for r in sruns if r["ok"])
        for s in c["sensitivity"]:
            res["sensitivity"][s["name"]] = {}
            for a in arms:
                try:
                    sc = score_arm(c, six, s["name"], a)
                    sc["pass"] = sc["pass"] and res["main"][a].get("C0", {}).get("pass_", False)
                    res["sensitivity"][s["name"]][a] = sc
                except KeyError as e:
                    res["sensitivity"][s["name"]][a] = dict(pass_=None, error=f"missing run {e}")
    passing = [a for a in arms if res["main"][a].get("pass")]
    robust = [a for a in passing if all(res["sensitivity"].get(s["name"], {}).get(a, {}).get("pass")
                                        for s in c["sensitivity"])]
    res["passing_arms"], res["robust_arms"] = passing, robust
    res["verdict"] = ("UNINTERPRETABLE" if res["failed_runs"] or any(res["main"][a].get("at_threshold")
                                                                     for a in passing) else
                      "PASS" if robust else "PASS (not robust)" if passing else "FAIL")
    (HERE / "outputs" / "analysis.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"{'arm':28s} C0 C1 C2 C3 C4 C5  pass")
    for a in arms:
        s = res["main"][a]
        cells = " ".join(("P " if s[k]["pass_"] else "F ") if k in s else "- " for k in ["C0", "C1", "C2", "C3", "C4", "C5"])
        print(f"{a:28s} {cells} {s.get('pass')}")
    print("verdict:", res["verdict"], "| passing:", passing, "| robust:", robust)


if __name__ == "__main__":
    main()
