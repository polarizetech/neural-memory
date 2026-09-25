"""E03-synthesis-block -- the ONLY entry point that produces citable E03 results (PREREG_PROTOCOL.md section 1).

    .venv/bin/python experiments/E03-synthesis-block/run.py --gates     # check the gates, run nothing
    .venv/bin/python experiments/E03-synthesis-block/run.py main        # 16 arms x Rajan 2026 protocols, + R1-R8
    .venv/bin/python experiments/E03-synthesis-block/run.py sensitivity # the same at each sensitivity setting
    .venv/bin/python experiments/E03-synthesis-block/run.py content     # descriptive content checks (PREREG 2, D1-D5)
    .venv/bin/python experiments/E03-synthesis-block/run.py export      # viewer traces

It REFUSES to run unless:
  * the tag E03-synthesis-block-prereg exists, and every FROZEN file is identical to it;
  * src/ is identical to the model tag named in config.yaml;
  * PREREG.md has all eleven sections; every package pinned in ENV.lock is installed at that version.
The model is deterministic: no seeds, no pooled workers. Nothing reads a result back into a parameter.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import subprocess
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
EID = HERE.name
sys.path.insert(0, str(REPO / "src"))

import yaml  # noqa: E402

FROZEN = ["PREREG.md", "config.yaml", "ENV.lock", "run.py", "analyse.py"]
SECTIONS = [f"## {i}." for i in range(1, 12)]


def git(*a) -> str:
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()


def load_cfg() -> dict:
    return yaml.safe_load((HERE / "config.yaml").read_text())


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


def gates() -> dict:
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
    elif subprocess.run(["git", "diff", "--quiet", mt, "--", "src"], cwd=REPO).returncode != 0 or \
            git("status", "--porcelain", "--", "src"):
        problems.append(f"src/ differs from {mt}")
    text = (HERE / "PREREG.md").read_text() if (HERE / "PREREG.md").exists() else ""
    missing = [s for s in SECTIONS if not re.search(rf"^{re.escape(s)}", text, re.M)]
    if missing:
        problems.append(f"PREREG.md is missing sections {missing}")
    problems += env_problems()
    return dict(tag=tag, commit=commit or None, model_tag=mt, problems=problems)


# ------------------------------------------------------------------------------------------------ arms, protocols
def arms(c: dict) -> list[dict]:
    a = c["arms"]
    return [dict(recycling=r, mechanism=m, k_deg_scale=k)
            for r, m, k in itertools.product(a["recycling"], a["mechanism"], a["k_deg_scale"])]


def arm_name(a: dict) -> str:
    return f"{a['recycling'][:3]}-{a['mechanism'][:4]}-kd{a['k_deg_scale']:g}"


def cell(a: dict, k_x: float, block: bool, n_channels: int = 1):
    from neurotape.singlecell.models import CellConfig
    return CellConfig(n_channels=n_channels, mechanism=a["mechanism"], recycling=a["recycling"],
                      k_deg_scale=a["k_deg_scale"], k_x=k_x, synthesis_scale=0.0 if block else 1.0,
                      block_from_min=0.0)


def protocol(c: dict, name: str, force: dict):
    """Returns (stims, n_training, t_end). Training taps come first; test taps (if any) follow."""
    from neurotape.singlecell.sim import Stim, train
    p = c["protocols"][name]
    if name.startswith("untrained"):
        levels = p.get("levels", [p.get("level")])
        return [], 0, max(p["tap_at_min"]), levels, p["tap_at_min"]
    F = force[p["level"]]
    st = train(p["pre_min"] - p["period_min"], F, p["period_min"], p["n"])
    if "test_after_min" in p:
        last = st[-1].t
        st += [Stim(last + d, 0, F, "stim") for d in p["test_after_min"]]
    return st, p["n"], st[-1].t, None, None


def run_protocol(c, a, k_x, force, name, block) -> dict:
    from neurotape.singlecell import sim
    cfg = cell(a, k_x, block)
    st, n, t_end, levels, taps = protocol(c, name, force)
    if levels is None:
        r = sim.run(cfg, st, t_end=t_end, sample_dt=1.0)
        ev = r["events"]
        return dict(p=[e["p_response"] for e in ev], S=[e["S_before"] for e in ev], V=[e["V"] for e in ev],
                    t=[e["t"] for e in ev], n_train=n)
    # untrained: each (level, tap time) is a separate naive cell given ONE tap
    out = {}
    for lv in levels:
        for t in taps:
            r = sim.run(cfg, [sim.Stim(t, 0, force[lv], "stim")], sample_dt=1.0)
            out[f"{lv}@{t:g}"] = r["events"][0]["p_response"]
    return dict(untrained=out)


def one_setting(c: dict, setting: dict) -> list[dict]:
    force = setting.get("force", c["force"])
    k_x = setting.get("k_x", c["arms"]["k_x"])
    rows = []
    for a in arms(c):
        for name in c["protocols"]:
            for block in (False, True):
                row = dict(arm=arm_name(a), **a, setting=setting["name"], protocol=name, block=block,
                           force=force, k_x=k_x)
                try:
                    row.update(ok=True, **run_protocol(c, a, k_x, force, name, block))
                except Exception:
                    row.update(ok=False, error=traceback.format_exc())
                rows.append(row)
    return rows


def gate_rows(c: dict) -> list[dict]:
    """R1-R8 with the block off. k_x cannot matter without a block (X stays at 1), so once per arm."""
    from neurotape.singlecell import gate
    rows = []
    for a in arms(c):
        cfg = cell(a, c["arms"]["k_x"], block=False)
        try:
            res = gate.check(cfg)
            rows.append(dict(arm=arm_name(a), **a, ok=True, gate=res))
        except Exception:
            rows.append(dict(arm=arm_name(a), **a, ok=False, error=traceback.format_exc()))
    return rows


# ------------------------------------------------------------------------------------------------ content (D1-D5)
def content_rows(c: dict) -> dict:
    from neurotape.singlecell import sim
    lo = c["gate_levels"]["low"]
    out = {}
    for a in arms(c):
        k_x = c["arms"]["k_x"]
        # D1 modality: train channel 0 for 60 taps, probe channel 1 (naive) and channel 0
        r2 = sim.run(cell(a, k_x, False, n_channels=2),
                     sim.sequence([(lo, 1, 60)], channel=0) + [sim.Stim(61, 1, lo, "probe"), sim.Stim(61, 0, lo, "probe")])
        naive = sim.run(cell(a, k_x, False), [sim.Stim(1, 0, lo, "probe")])["events"][0]["p_response"]
        d1 = dict(naive=naive, other_channel=r2["events"][-2]["p_response"], trained_channel=r2["events"][-1]["p_response"])
        # D3 history metamers: two different histories; find the rest time at which history 2's state is
        # closest to history 1's, then compare the next 30 responses
        h1 = sim.run(cell(a, k_x, False), sim.sequence([(lo, 1, 30)]), t_end=40, sample_dt=0.25)
        h2 = sim.run(cell(a, k_x, False), sim.sequence([(lo, 0.25, 60)]), t_end=15 + 120, sample_dt=0.25)
        s1, i1 = h1["trace"]["S0"][-1], h1["trace"]["I0"][-1]
        tr = h2["trace"]
        j = min(range(len(tr["t"])), key=lambda k: (tr["S0"][k] - s1) ** 2 + (tr["I0"][k] - i1) ** 2)
        d3 = dict(state1=(s1, i1), state2=(tr["S0"][j], tr["I0"][j]), t2=tr["t"][j],
                  dist=((tr["S0"][j] - s1) ** 2 + (tr["I0"][j] - i1) ** 2) ** 0.5)
        # D4 polarisation: receptor potential at each tap, 60 low taps; threshold fixed
        r = sim.run(cell(a, k_x, False), sim.sequence([(lo, 1, 60)]))
        d4 = dict(V_first=r["events"][0]["V"], V_last=r["events"][-1]["V"], V_th=0.012)
        # D5 longest memory: after the 12 h control training, minutes until p (level 4 probe) is within 0.05 of naive
        F4 = c["force"]["level4"]
        seq = sim.sequence([(F4, 1, 720)]) + sim.sequence([(0, 5, 24 * 12)], t0=720)
        rr = sim.run(cell(a, k_x, False), seq, probe_force=F4, sample_dt=1.0)
        naive4 = sim.run(cell(a, k_x, False), [sim.Stim(1, 0, F4, "probe")])["events"][0]["p_response"]
        pp = [e for e in rr["events"] if e["kind"] == "probe"]
        back = next((e["t"] - 720 for e in pp if e["p_response"] >= naive4 - 0.05), None)
        out[arm_name(a)] = dict(D1=d1, D3=d3, D4=d4, D5=dict(naive=naive4, minutes_to_within_0p05=back))
    return out


# ------------------------------------------------------------------------------------------------ exports
def exports(c: dict) -> list[str]:
    from neurotape.singlecell.export import export
    from neurotape.monorepo import stamp
    d = HERE / "outputs" / "export"
    d.mkdir(parents=True, exist_ok=True)
    made = []
    for a in c["exports"]:
        for name in ("puro_short", "long"):
            for block in (False, True):
                st, _, t_end, _, _ = protocol(c, name, c["force"])
                fn = d / f"{arm_name(a)}_{name}_{'block' if block else 'control'}.json"
                export(fn, cell(a, c["arms"]["k_x"], block), st, title=f"{arm_name(a)} {name} {'block' if block else 'control'}",
                       notes=[f"{EID}; Rajan 2026 protocol {name}"], channel_names=["mechanical"], t_end=t_end + 30,
                       probe_force=None, sample_dt=1.0, seed=0, provenance=dict(eid=EID, commit=git("rev-parse", "HEAD")))
                made.append(str(fn.relative_to(HERE)))
    (d / "provenance.json").write_text(json.dumps(stamp(["tools/result-provenance"]), indent=1, default=str))
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", nargs="?", choices=["main", "sensitivity", "content", "export"])
    ap.add_argument("--gates", action="store_true", help="check the gates and exit; runs nothing")
    a = ap.parse_args()
    g = gates()
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
    if a.stage == "main":
        runs = one_setting(c, dict(name="main"))
        (d / "runs.json").write_text(json.dumps(runs, indent=1, default=float))
        gr = gate_rows(c)
        (d / "gate.json").write_text(json.dumps(gr, indent=1, default=float))
        print(f"main {sum(r['ok'] for r in runs)}/{len(runs)} ok; gate {sum(r['ok'] for r in gr)}/{len(gr)} ok")
    elif a.stage == "sensitivity":
        runs = [r for s in c["sensitivity"] for r in one_setting(c, s)]
        (d / "runs.json").write_text(json.dumps(runs, indent=1, default=float))
        print(f"sensitivity {sum(r['ok'] for r in runs)}/{len(runs)} ok")
    elif a.stage == "content":
        (d / "content.json").write_text(json.dumps(content_rows(c), indent=1, default=float))
    else:
        print("\n".join(exports(c)))
    (d / "provenance.json").write_text(json.dumps(stamp(["tools/result-provenance"]), indent=1, default=str))
    lines = [f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.relative_to(HERE / 'outputs')}"
             for f in sorted((HERE / "outputs").rglob("*.json"))]
    (HERE / "outputs" / "SHA256SUMS").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()


