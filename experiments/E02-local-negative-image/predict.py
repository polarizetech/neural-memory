"""E02 analytic predictions -- computed BEFORE the -prereg tag, on the OFF-LIST prediction seeds (config.yaml
`prediction_seeds`), from the mean-field pools of habituation/analytic.py. No network is built; no on-list seed is
touched. Output: predictions/predictions.json (+ a table printed for PREREG section 3).

What it predicts is EFFICACY of the relay->E synapses (fast x slow pool x surface receptors), footprint-weighted per
probe. The network's spike response is a thresholded, inhibition-shaped function of efficacy, so spike-based
suppression can be larger or smaller than these numbers; PREREG states which criteria are judged against which.

Arms with no mean-field form (H: Hebbian, gated by postsynaptic firing; B: iSTDP) are NOT predicted here.

    .venv/bin/python experiments/E02-local-negative-image/predict.py [--workers 8]
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run as R  # noqa: E402  (same folder; importing runs nothing)

import numpy as np  # noqa: E402

PROBES = R.PROBES


def arm_variants(c):
    """(label, arm, extra config) for the arms with a mean-field form."""
    out = [("A", "A", None)]
    for v in c["arms"]["R"]["variants"]:
        out.append((f"R/{v['name']}", "R", v["config"]))
    return out


def predict_seed(seed: int) -> dict:
    from neurotape.habituation import analytic as An
    from neurotape.habituation.periphery import Periphery
    c = R.load_cfg()
    s = c["stimulus"]
    stim = R.stimuli_for_seed(seed)
    probes = {p: R.spec_from_json(stim["probes"][p]["spec"]) for p in PROBES}
    per = Periphery(R.arm_cfg(c, "Z", seed))
    rate = {p: per.relay_rate(probes[p]) for p in PROBES}
    r0 = per.cfg.periphery.relay_spont_hz
    n_cf = rate["A"].shape[1]
    out = dict(seed=seed, overlap={p: stim["probes"][p]["overlap"] for p in PROBES},
               drive_mismatch={p: stim["probes"][p]["drive_mismatch"] for p in PROBES}, arms={})
    for label, arm, extra in arm_variants(c):
        cfg_run = R.arm_cfg(c, arm, seed, extra)
        cfg_init = R.arm_cfg(c, arm, seed)                  # naive steady state: synthesis unblocked, S = 1
        # the block acts from network build, i.e. the pools start at the unblocked steady state and run blocked
        res = {}
        for sched in c["schedules"]:
            blocks, gap = R.schedule(c, sched)
            tr = An.naive_pools(cfg_init, n_cf)
            ctl = An.naive_pools(cfg_init, n_cf)
            E_train, elapsed = [], 0.0
            for bi, nb in enumerate(blocks):
                for k in range(nb):
                    E_train.append(An.pool_efficacy(tr, rate["A"], r0))
                    tr = An.present_pools(cfg_run, tr, rate["A"])
                    tr = An.silence_pools(cfg_run, tr, s["isi_s"] - s["duration_s"])
                    elapsed += s["isi_s"]
                if bi + 1 < len(blocks):
                    tr = An.silence_pools(cfg_run, tr, gap)
                    elapsed += gap
            ctl = An.silence_pools(cfg_run, ctl, elapsed)
            naive = An.naive_pools(cfg_init, n_cf)
            rows, t_tr, t_ctl, last = [], tr, ctl, 0.0
            for d in c["delays_s"]:
                t_tr = An.silence_pools(cfg_run, t_tr, d - last)
                t_ctl = An.silence_pools(cfg_run, t_ctl, d - last)
                last = d
                e_tr = {p: An.pool_efficacy(t_tr, rate[p], r0) for p in PROBES}
                e_ctl = {p: An.pool_efficacy(t_ctl, rate[p], r0) for p in PROBES}
                e_naive = {p: An.pool_efficacy(naive, rate[p], r0) for p in PROBES}
                S = {p: 1 - e_tr[p] / e_ctl[p] for p in PROBES}
                rows.append(dict(delay_s=d, S=S, SR={p: S["A"] - S[p] for p in c["analysis"]["map_probes"]},
                                 ctl_vs_naive={p: e_ctl[p] / e_naive[p] - 1 for p in PROBES}))
            E = np.array(E_train)
            k1 = c["analysis"]["first_k"]
            E1 = E[:k1].mean()
            thr = E1 - 0.5 * (E1 - E[-1])
            half = next((i + 1 for i, v in enumerate(E) if v <= thr), None) if E1 > E[-1] else None
            res[sched] = dict(E_train=E.tolist(), D=float(1 - E[-c["analysis"]["last_k"]:].mean() / E1),
                              half=half, probes=rows)
        out["arms"][label] = res
    return out


def summarise(runs, c):
    """Across prediction seeds: mean and range of each predicted quantity."""
    sesoi = c["analysis"]["sesoi"]
    summ = {}
    labels = list(runs[0]["arms"])
    delays = c["delays_s"]
    for label in labels:
        summ[label] = {}
        for sched in c["schedules"]:
            a = [r["arms"][label][sched] for r in runs]
            per_delay = []
            for i, d in enumerate(delays):
                SR = {p: [x["probes"][i]["SR"][p] for x in a] for p in c["analysis"]["map_probes"]}
                SA = [x["probes"][i]["S"]["A"] for x in a]
                base = [x["probes"][i]["ctl_vs_naive"]["A"] for x in a]
                per_delay.append(dict(delay_s=d, S_A_mean=float(np.mean(SA)),
                                      SR_mean={p: float(np.mean(v)) for p, v in SR.items()},
                                      SR_min={p: float(np.min(v)) for p, v in SR.items()},
                                      ctl_vs_naive_A_mean=float(np.mean(base))))
            boundary = {}
            for p in c["analysis"]["map_probes"]:
                above = [row["delay_s"] for row in per_delay if row["SR_mean"][p] > sesoi]
                boundary[p] = max(above) if above else None
            summ[label][sched] = dict(D_mean=float(np.mean([x["D"] for x in a])),
                                      half=[x["half"] for x in a], per_delay=per_delay,
                                      boundary_delay_s=boundary)
    overl = {p: [r["overlap"][p] for r in runs] for p in PROBES}
    return dict(overlap={p: dict(mean=float(np.mean(v)), min=float(np.min(v)), max=float(np.max(v)))
                         for p, v in overl.items()}, arms=summ)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    c = R.load_cfg()
    with ProcessPoolExecutor(a.workers, mp_context=get_context("spawn")) as ex:
        runs = list(ex.map(predict_seed, c["prediction_seeds"]))
    summ = summarise(runs, c)
    d = HERE / "predictions"
    d.mkdir(exist_ok=True)
    (d / "predictions.json").write_text(json.dumps(dict(seeds=runs, summary=summ), indent=1, default=float))
    print(json.dumps(summ["overlap"], indent=1))
    for label, v in summ["arms"].items():
        for sched, x in v.items():
            print(f"\n== {label} / {sched}: D = {x['D_mean']:.3f}, half = {x['half']}, boundary = {x['boundary_delay_s']}")
            for row in x["per_delay"]:
                print(f"  {row['delay_s']:>6}s  S_A {row['S_A_mean']:+.3f}  SR " +
                      "  ".join(f"{p} {row['SR_mean'][p]:+.3f}" for p in row["SR_mean"]) +
                      f"  ctl/naive-1 {row['ctl_vs_naive_A_mean']:+.3f}")


if __name__ == "__main__":
    main()
