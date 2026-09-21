"""R1 -- score the authors' reference implementation (jlubo/memory-consolidation-stc, run unmodified) against
docs/repro/TARGET.md. Q and MI are computed twice: with the AUTHORS' analysis functions from their `_net_<t>.txt`
files, and with neurotape's re-implementation (experiments/repro_lt2021.py) from their spike raster -- the second
is the check that R2's metric code measures the same thing.

usage: python docs/repro/r1_analyse.py <dir with trial_*/> <path to memory-consolidation-stc/analysis> [out.json]
"""
import glob, json, os, sys
import numpy as np

trials_dir, analysis_dir = sys.argv[1], sys.argv[2]
sys.path.insert(0, analysis_dir); sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from calculateQ import calculateMeanRatesAndQ            # noqa: E402  (authors')
from calculateMIa import calculateMIa                     # noqa: E402  (authors')
from utilityFunctions import readWeightMatrixData         # noqa: E402  (authors')
from neurotape.experiments import repro_lt2021 as R      # noqa: E402

NL, N_CA = 40, 150
core = np.arange(N_CA)
rows = []
for td in sorted(glob.glob(os.path.join(trials_dir, "trial_?"))):
    seed = int(td[-1]); dirs = sorted(d for d in glob.glob(os.path.join(td, "*")) if os.path.isdir(d))
    d10 = [d for d in dirs if "10s-recall" in d]; d8 = [d for d in dirs if "8h-recall" in d]
    if not (d10 and d8 and os.path.exists(os.path.join(td, "DONE"))):
        rows.append(dict(ok=False, seed=seed, error="incomplete")); continue
    ts10, ts8 = os.path.basename(d10[0])[:17], os.path.basename(d8[0])[:17]
    _, _, _, v_learn = readWeightMatrixData(glob.glob(os.path.join(d10[0], "network_plots", "*_net_11.0.txt"))[0], NL)
    never = np.arange(N_CA, NL * NL); ctrl_assembly = np.random.default_rng(seed + 4242).choice(never, 75, replace=False)
    row = dict(ok=True, seed=seed)
    for key, d, ts, tr in (("10s", d10[0], ts10, "20.1"), ("8h", d8[0], ts8, "28810.1")):
        npath = os.path.join(d, "network_plots") + os.sep
        Q, _, v_as, _, v_ans, _, v_ctrl, _ = calculateMeanRatesAndQ(npath, ts, core, NL, tr, 0.5)
        _, _, _, v_rec = readWeightMatrixData(glob.glob(npath + f"*_net_{tr}.txt")[0], NL)
        MI = calculateMIa(v_learn, v_rec, output="none")[0]
        # neurotape's implementation, from the raster
        ras = np.loadtxt(glob.glob(os.path.join(d, "*_spike_raster.txt"))[0]); t, i = ras[:, 0], ras[:, 1].astype(int)
        e = i < NL * NL; t, i = t[e], i[e]
        vr = R.window_rates(i, t, float(tr), NL * NL)
        q2 = R.q_star(vr, np.arange(75), np.arange(75, 150), never)
        mi2 = None
        if key == "10s":
            vl = R.window_rates(i, t, 11.0, NL * NL); mi2 = R.mutual_information(vl, vr); row["_vl"] = vl
        elif "_vl" in row:
            mi2 = R.mutual_information(row["_vl"], vr)
        row[key] = dict(Q=float(Q), MI=float(MI), nu_as=float(v_as), nu_ans=float(v_ans), nu_ctrl=float(v_ctrl),
                        nu_control_assembly=float(v_rec.ravel()[ctrl_assembly].mean()), Q_neurotape_impl=q2["Q"], MI_neurotape_impl=mi2)
    row.pop("_vl", None); rows.append(row)

ok = [r for r in rows if r["ok"]]
runs = {k: [dict(ok=True, Q=r[k]["Q"], MI=r[k]["MI"], nu_ans=r[k]["nu_ans"], nu_control_assembly=r[k]["nu_control_assembly"]) for r in ok] for k in ("10s", "8h")}
sc = R.score(runs["10s"], runs["8h"], n_expected=len(rows))
out = dict(trials=rows, score=sc)
json.dump(out, open(sys.argv[3] if len(sys.argv) > 3 else "r1.json", "w"), indent=1, default=float)
for r in ok:
    print(r["seed"], " ".join(f"{k}: Q {r[k]['Q']:.4f} (impl {r[k]['Q_neurotape_impl']:.4f}) MI {r[k]['MI']:.4f} (impl {r[k]['MI_neurotape_impl']:.4f}) ans {r[k]['nu_ans']:.2f} ctrlA {r[k]['nu_control_assembly']:.2f}" for k in ("10s", "8h")))
print(json.dumps({k: v for k, v in sc.items()}, indent=1, default=float))
