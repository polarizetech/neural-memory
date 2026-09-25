"""E02-local-negative-image -- the ONLY entry point that produces citable E02 results (PREREG_PROTOCOL.md section 1).

    .venv/bin/python experiments/E02-local-negative-image/run.py --gates        # check the gates, run nothing
    .venv/bin/python experiments/E02-local-negative-image/run.py stimuli        # stage 0: per-seed probe set
    .venv/bin/python experiments/E02-local-negative-image/run.py control|main|sensitivity --workers 8

Stages run in the order PREREG section 9 fixes: `stimuli` (no network), then `control` (arm Z, plasticity off: it
calibrates the MDE and must exist before any other arm is analysed), then `main`, then `sensitivity`.

It REFUSES to run a simulation unless:
  * the tag E02-local-negative-image-prereg exists (its commit is printed);
  * every FROZEN file is identical to that tag, and src/ is identical to the model tag named in config.yaml;
  * PREREG.md has all ten sections; every package pinned in ENV.lock is installed at that version;
  * (main, sensitivity) outputs/stimuli/stimuli.json and outputs/control/runs.json exist.
Nothing here reads a result back into a parameter. Every job is kept, failed ones included.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, replace
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
EID = HERE.name
os.environ.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", VECLIB_MAXIMUM_THREADS="1")
sys.path.insert(0, str(REPO / "src"))

import numpy as np  # noqa: E402
import yaml  # noqa: E402

FROZEN = ["PREREG.md", "config.yaml", "ENV.lock", "run.py", "analyse.py", "predict.py", "predictions/predictions.json"]
SECTIONS = [f"## {i}." for i in range(1, 11)]


def git(*a) -> str:
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()


def gates(stage: str | None = None) -> dict:
    cfg = load_cfg()
    tag = f"{EID}-prereg"
    commit = git("rev-parse", "-q", "--verify", f"refs/tags/{tag}^{{commit}}")
    problems = []
    if not commit:
        problems.append(f"no {tag} tag: write PREREG.md and tag it with .agents/tools/tag first")
    else:
        for f in FROZEN:
            rel = f"experiments/{EID}/{f}"
            if subprocess.run(["git", "diff", "--quiet", tag, "--", rel], cwd=REPO).returncode != 0 or \
                    git("status", "--porcelain", "--", rel):
                problems.append(f"{rel} differs from {tag}")
    mt = cfg["model_tag"]
    if not git("rev-parse", "-q", "--verify", f"refs/tags/{mt}"):
        problems.append(f"model tag {mt} does not exist")
    elif subprocess.run(["git", "diff", "--quiet", mt, "--", "src"], cwd=REPO).returncode != 0 or git("status", "--porcelain", "--", "src"):
        problems.append(f"src/ differs from {mt}")
    text = (HERE / "PREREG.md").read_text() if (HERE / "PREREG.md").exists() else ""
    missing = [s for s in SECTIONS if not re.search(rf"^{re.escape(s)}", text, re.M)]
    if missing:
        problems.append(f"PREREG.md is missing sections {missing}")
    problems += env_problems()
    if stage in ("main", "sensitivity"):
        for need in ("outputs/stimuli/stimuli.json", "outputs/control/runs.json"):
            if not (HERE / need).exists():
                problems.append(f"{need} missing: stage order is stimuli -> control -> main -> sensitivity")
    return dict(tag=tag, commit=commit or None, model_tag=mt, problems=problems)


def env_problems() -> list[str]:
    from importlib import metadata
    out = []
    for line in (HERE / "ENV.lock").read_text().splitlines():
        m = re.match(r"^([A-Za-z0-9_.\-]+)==([^\s;\\]+)", line)
        if not m:
            continue
        name, ver = m.groups()
        try:
            have = metadata.version(name)
        except metadata.PackageNotFoundError:
            out.append(f"ENV.lock pins {name}=={ver}; not installed")
            continue
        if have != ver:
            out.append(f"ENV.lock pins {name}=={ver}; installed {have}")
    return out


# ------------------------------------------------------------------------------------------------ config
def load_cfg():
    return yaml.safe_load((HERE / "config.yaml").read_text())


def arm_cfg(c, arm: str, seed: int, extra: dict | None = None):
    from neurotape.experiments.habituation import _merge
    from neurotape.habituation.config import HabConfig, load
    base = load(REPO / c["base_config"]).model_dump()
    d = _merge(_merge(base, c["common"]), c["arms"][arm]["config"])
    if extra:
        d = _merge(d, extra)
    return HabConfig.model_validate({**d, "seed": int(seed)})


# ------------------------------------------------------------------------------------------------ stage 0: stimuli
def spec_to_json(s) -> dict:
    return asdict(s)


def spec_from_json(d):
    from neurotape.habituation.stimuli import SoundSpec
    return SoundSpec(**{k: tuple(v) if isinstance(v, list) else v for k, v in d.items()})


def _driven_sum(per, spec, r0):
    return float(np.clip(per.relay_rate(spec).mean(0) - r0, 0, None).sum())


def _level_match(per, spec, target, r0, base_db, it=4):
    """B's level (dB SPL) so its driven relay sum is within 5 % of A's. Secant on the periphery only."""
    from neurotape.habituation.stimuli import louder
    lv0, lv1 = base_db, base_db + 3.0
    f = lambda lv: _driven_sum(per, replace(spec, level_db=lv), r0) - target
    f0, f1 = f(lv0), f(lv1)
    for _ in range(it):
        if abs(f1) <= 0.05 * target or f1 == f0:
            break
        lv0, lv1, f0 = lv1, lv1 - f1 * (lv1 - lv0) / (f1 - f0), f1
        lv1 = float(np.clip(lv1, base_db - 15, base_db + 15))
        f1 = f(lv1)
    return replace(spec, level_db=float(lv1)), abs(f1) / target


def stimuli_for_seed(seed: int) -> dict:
    """The probe set for one seed: exposed A, and unexposed B at three overlap levels (PREREG section 9, items 1-3).
    Reads the periphery only; no network exists here."""
    from neurotape.habituation import analytic as An
    from neurotape.habituation.periphery import Periphery
    from neurotape.habituation.stimuli import draw, family, variant
    c = load_cfg()
    s = c["stimulus"]
    cfg = arm_cfg(c, "Z", seed)
    per = Periphery(cfg)
    r0 = cfg.periphery.relay_spont_hz
    fam = family(seed, s["duration_s"], 0, [])
    A = fam.stored
    rA = per.relay_rate(A)
    target = _driven_sum(per, A, r0)
    out = {"A": dict(spec=spec_to_json(A), overlap=1.0, drive_mismatch=0.0)}
    # full: the time-reversed sound (identical long-term spectrum)
    full = variant(A, "reversed")
    out["full"] = dict(spec=spec_to_json(full), overlap=An.overlap(rA, per.relay_rate(full), r0),
                       drive_mismatch=abs(_driven_sum(per, full, r0) - target) / target)
    # partial: the shift whose overlap is closest to the target, inside the band
    o = c["overlap"]
    best = None
    for k in o["partial_shifts_oct"]:
        v = variant(A, "shift", k)
        ov = An.overlap(rA, per.relay_rate(v), r0)
        if best is None or abs(ov - o["partial_target"]) < abs(best[1] - o["partial_target"]):
            best = (v, ov)
    v, ov = best
    v, mm = _level_match(per, v, target, r0, cfg.periphery.level_db_spl)
    out["partial"] = dict(spec=spec_to_json(v), overlap=An.overlap(rA, per.relay_rate(v), r0), drive_mismatch=mm,
                          in_band=bool(o["partial_band"][0] <= ov <= o["partial_band"][1]))
    # none: the lowest-overlap of a FIXED number of independent draws (a ceiling on overlap proved unreachable: at
    # 60 dB any 4-component sound excites most AN channels; see PREREG section 9 item 2)
    rng = np.random.default_rng(seed + o["none_rng_offset"])
    cands = []
    for j in range(o["none_n_draws"]):
        v = draw(rng, f"none{j:02d}", s["duration_s"])
        cands.append((An.overlap(rA, per.relay_rate(v), r0), j, v))
    ov, _, v = min(cands, key=lambda x: (x[0], x[1]))
    v, mm = _level_match(per, v, target, r0, cfg.periphery.level_db_spl)
    out["none"] = dict(spec=spec_to_json(v), overlap=An.overlap(rA, per.relay_rate(v), r0), drive_mismatch=mm)
    return dict(seed=seed, probes=out)


def _stim_job(seed):
    try:
        return dict(ok=True, **stimuli_for_seed(seed))
    except Exception as e:
        return dict(ok=False, seed=seed, error=f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-2000:])


# ------------------------------------------------------------------------------------------------ one job
PROBES = ["A", "full", "partial", "none"]


def schedule(c, name):
    """(block sizes, gap between blocks in s)."""
    sc = c["schedules"][name]
    return sc["blocks"], sc["gap_s"]


def _driven(rec, t0, t1, spont_hz, n_exc, dt):
    """E spikes in steps [t0, t1) minus the expected spontaneous count, per batch copy."""
    return rec.e_count[t0:t1].sum(0).astype(float) - spont_hz * n_exc * (t1 - t0) * dt


def job(j) -> dict:
    try:
        from neurotape.habituation.protocol import make_sim
        from neurotape.habituation.model import run
        c = load_cfg()
        arm, sched, seed, var = j["arm"], j["schedule"], j["seed"], j.get("variant", {})
        s = c["stimulus"]
        extra = var.get("config")
        cfg = arm_cfg(c, arm, seed, extra)
        stim = json.loads((HERE / "outputs/stimuli/stimuli.json").read_text())
        probes = {p: spec_from_json(stim[str(seed)]["probes"][p]["spec"]) for p in PROBES}
        sim, st0 = make_sim(cfg)
        dt, NE = sim.dt, cfg.network.n_exc
        spont = sim.rate_e_spont
        n_stim = int(round(s["duration_s"] / dt))
        w_on = [int(round(x / dt)) for x in s["onset_window_s"]]
        w_su = [int(round(x / dt)) for x in s["sustained_window_s"]]
        gains = c["arms"][arm].get("gain_steps")
        gains_at = c["arms"][arm].get("gain_steps_at")
        blocks, gap = schedule(c, sched)

        # ---------------- training (and the matched control's clock)
        st = st0.copy()
        rng = np.random.default_rng(seed + 4242)
        R, onset_cells, sust_cells = [], [], []
        elapsed = 0.0
        n_pres = 0
        for bi, nb in enumerate(blocks):
            for k in range(nb):
                if gains is not None and n_pres in gains_at:
                    st.g_in = np.full(1, gains[gains_at.index(n_pres)])
                n_pres += 1
                rec = run(sim.net, st, sim.raster(probes["A"], rng), rng, keep_cells=True)
                R.append(float(_driven(rec, 0, n_stim, spont, NE, dt)[0]))
                onset_cells.append(rec.cells_t[w_on[0]:w_on[1], 0].sum(0).tolist())
                sust_cells.append(rec.cells_t[w_su[0]:w_su[1], 0].sum(0).tolist())
                sim.quiet(st, s["isi_s"] - s["duration_s"], rng)
                elapsed += s["isi_s"]
            if bi + 1 < len(blocks):
                sim.advance(st, gap, np.random.default_rng(seed + 77 + bi))
                elapsed += gap

        # ---------------- probes: every delay, trained and control, pathway intact and removed (separate paired calls)
        prng = np.random.default_rng(seed + 9001)
        rasters = np.stack([sim.raster(probes[p], prng, s["probe_tail_s"]) for p in PROBES])
        win = n_stim
        out = []
        for d in c["delays_s"]:
            tr = st.copy()
            sim.advance(tr, d, np.random.default_rng(seed + 77))
            ctl = st0.copy()
            sim.advance(ctl, elapsed + d, np.random.default_rng(seed + 77))
            row = dict(delay_s=d)
            for tag, net_state in (("tr", tr), ("ctl", ctl)):
                for rm in (False, True):
                    x = net_state.copy()
                    if rm:
                        if x.ff_out is None:
                            raise RuntimeError("removal requested with no FF pathway")
                        x.ff_out[:] = 0.0
                    rec = sim.probe(x, rasters, seed + 55)
                    key = f"{tag}_{'off' if rm else 'on'}"
                    row[key] = dict(zip(PROBES, _driven(rec, 0, win, spont, NE, dt).tolist()))
                    row[key + "_onset"] = dict(zip(PROBES, _driven(rec, w_on[0], w_on[1], spont, NE, dt).tolist()))
                    row[key + "_sust"] = dict(zip(PROBES, _driven(rec, w_su[0], w_su[1], spont, NE, dt).tolist()))
            if tr.G is not None:
                conn = sim.net.W_fe > 0
                row["G_mean"] = float(tr.G[0][conn].mean())
            if tr.Srec is not None:
                row["S_mean"] = float(tr.Srec.mean())
                row["S_mean_ctl"] = float(ctl.Srec.mean())
            out.append(row)
        return dict(ok=True, arm=arm, schedule=sched, seed=seed, variant=var.get("name", "base"), spont_hz=spont,
                    R_train=R, onset_cells=onset_cells, sust_cells=sust_cells, elapsed_training_s=elapsed,
                    probes=out)
    except Exception as e:
        return dict(ok=False, arm=j["arm"], schedule=j["schedule"], seed=j["seed"],
                    variant=j.get("variant", {}).get("name", "base"),
                    error=f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-2000:])


def jobs_for(stage: str, c) -> list[dict]:
    J = []
    if stage == "control":
        for sc in c["schedules"]:
            for sd in c["seeds"]:
                J.append(dict(arm="Z", schedule=sc, seed=sd))
    elif stage == "main":
        for arm, a in c["arms"].items():
            if arm == "Z":
                continue
            for v in a.get("variants", [dict(name="base")]):
                for sc in c["schedules"]:
                    for sd in c["seeds"]:
                        J.append(dict(arm=arm, schedule=sc, seed=sd, variant=v))
    elif stage == "sensitivity":
        for v in c["sensitivity"]["variants"]:
            for sc in c["schedules"]:
                for sd in c["sensitivity"]["seeds"]:
                    J.append(dict(arm=v["arm"], schedule=sc, seed=sd, variant=v))
    return J


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", nargs="?", choices=["stimuli", "control", "main", "sensitivity"])
    ap.add_argument("--gates", action="store_true", help="check the gates and exit; runs nothing")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    g = gates(a.stage)
    print(f"[{EID}] prereg tag {g['tag']} -> {g['commit']}; model tag {g['model_tag']}")
    for pr in g["problems"]:
        print("  GATE:", pr)
    if a.gates or not a.stage:
        sys.exit(1 if g["problems"] else 0)
    if g["problems"]:
        sys.exit("refusing to run: the gates above failed (PREREG_PROTOCOL.md rule 1)")
    c = load_cfg()
    from neurotape.monorepo import stamp
    d = HERE / "outputs" / a.stage
    d.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(a.workers, mp_context=get_context("spawn")) as ex:
        if a.stage == "stimuli":
            runs = list(ex.map(_stim_job, c["seeds"] + c["sensitivity"]["seeds_extra"]))
            (d / "stimuli.json").write_text(json.dumps({str(r["seed"]): r for r in runs}, indent=1, default=float))
        else:
            runs = list(ex.map(job, jobs_for(a.stage, c)))
            (d / "runs.json").write_text(json.dumps(runs, indent=1, default=float))
    (d / "provenance.json").write_text(json.dumps(stamp(["tools/result-provenance"]), indent=1, default=str))
    print(a.stage, f"{sum(r['ok'] for r in runs)}/{len(runs)} ok ->", d, flush=True)
    lines = [f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.relative_to(HERE / 'outputs')}"
             for f in sorted((HERE / "outputs").rglob("*.json"))]
    (HERE / "outputs" / "SHA256SUMS").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
