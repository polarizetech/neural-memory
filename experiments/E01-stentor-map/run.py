"""E01-stentor-map -- the ONLY entry point that produces citable E01 results (PREREG_PROTOCOL.md section 1).

    .venv/bin/python experiments/E01-stentor-map/run.py --gates          # check the gates, run nothing
    .venv/bin/python experiments/E01-stentor-map/run.py sr1|sr2|sr3|all --workers 8

It REFUSES to run a simulation unless:
  * the tag E01-stentor-map-prereg exists (its commit is printed);
  * PREREG.md, config.yaml, ENV.lock, analyse.py and this file are identical to that tag;
  * src/ is identical to the model tag named in config.yaml;
  * PREREG.md has all ten sections;
  * every package pinned in ENV.lock is installed at that version.
Nothing here reads a result back into a parameter. Outputs: outputs/<part>/{runs.json, summary.json,
provenance.json}, outputs/SHA256SUMS. Every seed is kept, failed ones included.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
EID = HERE.name
os.environ.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", VECLIB_MAXIMUM_THREADS="1")
sys.path.insert(0, str(REPO / "src"))

import numpy as np  # noqa: E402
import yaml  # noqa: E402

FROZEN = ["PREREG.md", "config.yaml", "ENV.lock", "run.py", "analyse.py"]
SECTIONS = [f"## {i}." for i in range(1, 11)]


def git(*a) -> str:
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()


def gates() -> dict:
    cfg = yaml.safe_load((HERE / "config.yaml").read_text())
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


# ------------------------------------------------------------------------------------------------ helpers
def load_cfg():
    return yaml.safe_load((HERE / "config.yaml").read_text())


def arm_cfg(c, arm: str, seed: int):
    from neurotape.experiments.habituation import _merge
    from neurotape.habituation.config import HabConfig, load
    base = load(REPO / c["base_config"]).model_dump()
    return HabConfig.model_validate({**_merge(base, c["arms"][arm]), "seed": int(seed)})


def scaled(sim, cfg, param: str | None, scale: float):
    """The same network under a recovery rate multiplied by `scale` (0 = frozen). Applied at training onset."""
    if param is None or scale == 1.0:
        return sim
    c = cfg.model_copy(deep=True)
    sec, key = param.split(".")
    old = getattr(getattr(c, sec), key)
    setattr(getattr(c, sec), key, math.inf if scale == 0 else old / scale)
    return replace(sim, cfg=c, net=replace(sim.net, cfg=c))


def driven(rec, steps: int, spont_hz: float, n_exc: int, dt: float) -> np.ndarray:
    """E spikes in the first `steps` steps (the stimulus), minus the expected spontaneous count."""
    return rec.e_count[:steps].sum(0).astype(float) - spont_hz * n_exc * steps * dt


# ------------------------------------------------------------------------------------------------ SR1
def sr1(job) -> dict:
    try:
        from neurotape.habituation import measure as M
        from neurotape.habituation.protocol import make_sim
        from neurotape.habituation.stimuli import family
        c, arm, seed = load_cfg(), job["arm"], job["seed"]
        p, st_ = c["sr1"], c["stimulus"]
        cfg = arm_cfg(c, arm, seed)
        sim0, st0 = make_sim(cfg)
        fam = family(seed, st_["duration_s"], st_["n_novel"], [])
        dt, NE = sim0.dt, cfg.network.n_exc
        steps = int(round(st_["duration_s"] / dt))
        probes = [fam.stored] + fam.novel
        prng = np.random.default_rng(seed + 9001)
        rasters = np.stack([sim0.raster(s, prng, p["probe_tail_s"]) for s in probes])
        param = p["scaled_parameter"][arm]
        scales = p["recovery_scales"] if param else [1.0]
        out = []
        for sc in scales:
            sim = scaled(sim0, cfg, param, sc)
            st = st0.copy()
            rng = np.random.default_rng(seed + 4242)
            R = []
            for _ in range(p["n_presentations"]):
                rec = sim.present(st, fam.stored, rng)
                R.append(float(driven(rec, steps, sim0.rate_e_spont, NE, dt)[0]))
                sim.quiet(st, p["isi_s"] - st_["duration_s"], rng)
            sim.advance(st, p["delay_s"], np.random.default_rng(seed + 77))
            ctrl = st0.copy()
            sim.advance(ctrl, p["n_presentations"] * p["isi_s"] + p["delay_s"], np.random.default_rng(seed + 77))
            tr = sim.probe(st, rasters, seed + 55)
            cr = sim.probe(ctrl, rasters, seed + 55)
            win = steps + int(round(p["probe_tail_s"] / dt))
            Rt, Rc = tr.e_count[:win].sum(0).astype(float), cr.e_count[:win].sum(0).astype(float)
            spont_win = sim0.rate_e_spont * NE * win * dt
            S = M.suppression(Rt, Rc)
            R = np.array(R)
            thr = R[0] - 0.5 * (R[0] - R[-1])
            half = next((i + 1 for i, v in enumerate(R) if v <= thr), None) if R[0] > R[-1] else None
            half_abs = next((i + 1 for i, v in enumerate(R) if v <= 0.5 * R[0]), None)
            out.append(dict(scale=sc, R=R.tolist(), D16=float(1 - R[-1] / R[0]) if R[0] > 0 else None,
                            half=half, half_abs=half_abs, retention=float(S[0]),
                            recognition=float(S[0] - np.nanmean(S[1:])),
                            R_ctrl_stored=float(Rc[0]), R_tr_stored=float(Rt[0]), spont_expected=float(spont_win),
                            floor=bool(Rc[0] < p["floor_multiple"] * spont_win)))
        return dict(ok=True, part="sr1", arm=arm, seed=seed, spont_hz=sim0.rate_e_spont, results=out)
    except Exception as e:
        return dict(ok=False, part="sr1", arm=job["arm"], seed=job["seed"], error=f"{type(e).__name__}: {e}",
                    trace=traceback.format_exc()[-2000:])


# ------------------------------------------------------------------------------------------------ SR2
def onsets(rate: float, n: int, dur: float, schedule: str, rng) -> np.ndarray:
    T = 1.0 / rate
    if schedule == "periodic":
        return np.arange(n) * T
    span = (n - 1) * T                                 # same count, same total span as the periodic train
    g = dur + (span - (n - 1) * dur) * rng.dirichlet(np.ones(n - 1))   # uniform spacings, each >= the stimulus
    return np.concatenate([[0.0], np.cumsum(g)])


def sr2(job) -> dict:
    try:
        from neurotape.habituation.protocol import make_sim
        from neurotape.habituation.stimuli import family
        c, arm, seed = load_cfg(), job["arm"], job["seed"]
        p, st_ = c["sr2"], c["stimulus"]
        cfg = arm_cfg(c, arm, seed)
        sim, st0 = make_sim(cfg)
        fam = family(seed, st_["duration_s"], 1, [])
        dt, NE, dur = sim.dt, cfg.network.n_exc, st_["duration_s"]
        steps = int(round(dur / dt))
        out = []
        for sched in p["schedules"]:
            for f in p["rates_hz"]:
                on = onsets(f, p["n_presentations"], dur, sched, np.random.default_rng(seed * 1000 + int(f * 1000)))
                st, rng = st0.copy(), np.random.default_rng(seed + 4242)
                R = []
                for k in range(p["n_presentations"]):
                    rec = sim.present(st, fam.stored, rng)
                    R.append(float(driven(rec, steps, sim.rate_e_spont, NE, dt)[0]))
                    if k + 1 < p["n_presentations"]:
                        sim.advance(st, on[k + 1] - on[k] - dur, rng)
                R = np.array(R)
                D = float(1 - R[-p["steady_state_last"]:].mean() / R[0]) if R[0] > 0 else None
                out.append(dict(schedule=sched, rate_hz=f, onsets=on.tolist(), R=R.tolist(), D=D))
        return dict(ok=True, part="sr2", arm=arm, seed=seed, spont_hz=sim.rate_e_spont, results=out)
    except Exception as e:
        return dict(ok=False, part="sr2", arm=job["arm"], seed=job["seed"], error=f"{type(e).__name__}: {e}",
                    trace=traceback.format_exc()[-2000:])


# ------------------------------------------------------------------------------------------------ SR3
def sr3(job) -> dict:
    try:
        from neurotape.habituation.protocol import make_sim
        from neurotape.habituation.stimuli import family, louder, silence
        c, arm, seed = load_cfg(), job["arm"], job["seed"]
        p, st_ = c["sr3"], c["stimulus"]
        cfg = arm_cfg(c, arm, seed)
        sim, st0 = make_sim(cfg)
        fam = family(seed, st_["duration_s"], 1, [])
        dt, NE, dur = sim.dt, cfg.network.n_exc, st_["duration_s"]
        steps = int(round(dur / dt))
        out = {}
        for name, ins in p["inserts"].items():
            st, rng = st0.copy(), np.random.default_rng(seed + 4242)      # identical draws across inserts: paired
            R = []
            for k in range(1, p["n_presentations"] + 1):
                spec = fam.stored
                if k == p["insert_at"] and ins is not None:
                    spec = silence(dur) if ins == "silence" else louder(fam.stored, ins, st_["base_level_db"])
                rec = sim.present(st, spec, rng)
                R.append(float(driven(rec, steps, sim.rate_e_spont, NE, dt)[0]))
                sim.quiet(st, p["isi_s"] - dur, rng)
            out[name] = R
        k = p["scored_presentation"] - 1
        eff = {n: (out[n][k] / out["none"][k] - 1) if out["none"][k] > 0 else None for n in out if n != "none"}
        return dict(ok=True, part="sr3", arm=arm, seed=seed, spont_hz=sim.rate_e_spont, R=out, effect=eff)
    except Exception as e:
        return dict(ok=False, part="sr3", arm=job["arm"], seed=job["seed"], error=f"{type(e).__name__}: {e}",
                    trace=traceback.format_exc()[-2000:])


PARTS = {"sr1": (sr1, ["std", "hebb_only", "none"]), "sr2": (sr2, ["std", "hebb_only", "none"]),
         "sr3": (sr3, ["std", "hebb_only", "none"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("part", nargs="?", choices=[*PARTS, "all"])
    ap.add_argument("--gates", action="store_true", help="check the gates and exit; runs nothing")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    g = gates()
    print(f"[{EID}] prereg tag {g['tag']} -> {g['commit']}; model tag {g['model_tag']}")
    for pr in g["problems"]:
        print("  GATE:", pr)
    if a.gates or not a.part:
        sys.exit(1 if g["problems"] else 0)
    if g["problems"]:
        sys.exit("refusing to run: the gates above failed (PREREG_PROTOCOL.md rule 1)")
    c = load_cfg()
    parts = list(PARTS) if a.part == "all" else [a.part]
    from neurotape.monorepo import stamp
    for part in parts:
        fn, arms = PARTS[part]
        jobs = [dict(arm=arm, seed=s) for arm in arms for s in c["seeds"]]
        with ProcessPoolExecutor(a.workers, mp_context=get_context("spawn")) as ex:
            runs = list(ex.map(fn, jobs))
        d = HERE / "outputs" / part
        d.mkdir(parents=True, exist_ok=True)
        (d / "runs.json").write_text(json.dumps(runs, indent=1, default=float))
        (d / "provenance.json").write_text(json.dumps(stamp(["tools/result-provenance"]), indent=1, default=str))
        print(part, f"{sum(r['ok'] for r in runs)}/{len(runs)} ok ->", d, flush=True)
    lines = []
    for f in sorted((HERE / "outputs").rglob("*.json")):
        lines.append(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.relative_to(HERE / 'outputs')}")
    (HERE / "outputs" / "SHA256SUMS").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
