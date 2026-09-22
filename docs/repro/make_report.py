"""Build docs/repro/REPORT.md from docs/repro/runs/*.json. Only what was run is reported.

usage: .venv/bin/python docs/repro/make_report.py
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
from neurotape.experiments import repro_lt2021 as R      # noqa: E402

RUNS = HERE / "runs"
PAPER = dict(nu={"10s": (94.59, 10.56, 7.70), "8h": (94.71, 12.41, 9.10)}, **R.PAPER)


def ms(x, fmt="{:.4f}"):
    x = np.array([v for v in x if v is not None and np.isfinite(v)], float)
    if x.size == 0:
        return "—"
    return (fmt + " ± " + fmt).format(x.mean(), x.std(ddof=1) if x.size > 1 else float("nan"))


def yn(b):
    return "**pass**" if b else "**FAIL**"


def cond_table(names, delays=("10s", "8h"), label=None):
    out = "| condition | delay | seeds ok | ν_as (Hz) | ν_ans (Hz) | ν_ctrl (Hz) | Q, reference read-out | Q, true counts | MI (bits) | ν_ans > control assembly | standby E rate (Hz) |\n|---|---|---|---|---|---|---|---|---|---|---|\n"
    for rc in delays:
        a, b, c = PAPER["nu"][rc]
        out += f"| *paper* | {rc} | 10 | {a:.1f} | {b:.2f} | {c:.2f} | {PAPER['Q'][rc][0]:.4f} ± {PAPER['Q'][rc][1]:.4f} | — | {PAPER['MI'][rc][0]:.4f} ± {PAPER['MI'][rc][1]:.4f} | — | 0.5–1.0 (text) |\n"
    for name in names:
        rows, _, _ = R.condition_rows(name)
        for r in rows:
            if r["delay"] not in delays:
                continue
            out += (f"| {(label or {}).get(name, name)} | {r['delay']} | {r['n_ok']}/{r['n']} | {r['nu_as']} | {r['nu_ans']} | {r['nu_ctrl']} | {r['Q_ref']} | {r['Q']} | "
                    f"{r['MI']} | {r['b']}/{r['n']} | {r['standby']} |\n")
    return out


def criteria(sc):
    if sc is None:
        return "not scored (a delay is missing)\n"
    o = "| criterion | value | target | result |\n|---|---|---|---|\n"
    for m in ("Q", "MI"):
        for k in ("10s", "8h"):
            d = sc[f"{m}_{k}"]
            o += f"| (a) {m}({k.replace('s', ' s').replace('h', ' h')}) | {d['mean']:.4f} ± {d['sd']:.4f} (n = {d['n']}) | [{d['lo']:.4f}, {d['hi']:.4f}] | {yn(d['within'])} |\n"
    for k in ("10s", "8h"):
        o += f"| (b) ν_ans > control assembly, {k} | {sc[f'b_{k}']['n_pass']} of {sc[f'b_{k}']['n']} seeds | ≥ 8 | {yn(sc[f'b_{k}']['passed'])} |\n"
    o += f"| (c) improvement | Q {sc['gain_Q']:+.1%}, MI {sc['gain_MI']:+.1%} | both > 0 (paper +15 %, +12 %) | {yn(sc['c_pass'])} |\n"
    return o + f"\n**(a) {yn(sc['a_pass'])} · (b) {yn(sc['b_pass'])} · (c) {yn(sc['c_pass'])}**\n"


def tags_table(name):
    o = "| delay run | instant | within assembly: tags pot / dep | late-phase pot / dep | mean h / z | outside assembly: tags pot / dep | late-phase pot / dep | protein: assembly / rest |\n|---|---|---|---|---|---|---|---|\n"
    for rc in ("10s", "8h"):
        rs = R._load(name, rc)
        if not rs:
            continue
        ok = [r for r in rs if r.get("ok")]
        for inst in ok[0]["tags"]:
            g = lambda part, key: np.mean([r["tags"][inst][part][key] for r in ok])
            o += (f"| {rc} | {inst} | {g('within_assembly', 'tag_pot'):.0f} / {g('within_assembly', 'tag_dep'):.0f} of {g('within_assembly', 'n'):.0f} | "
                  f"{g('within_assembly', 'late_pot'):.0f} / {g('within_assembly', 'late_dep'):.0f} | {g('within_assembly', 'mean_h'):.3f} / {g('within_assembly', 'mean_z'):.3f} | "
                  f"{g('outside_assembly', 'tag_pot'):.0f} / {g('outside_assembly', 'tag_dep'):.0f} of {g('outside_assembly', 'n'):.0f} | "
                  f"{g('outside_assembly', 'late_pot'):.0f} / {g('outside_assembly', 'late_dep'):.0f} | "
                  f"{np.mean([r['protein'][inst]['assembly'] for r in ok]):.3f} / {np.mean([r['protein'][inst]['rest'] for r in ok]):.3f} |\n")
    return o


if __name__ == "__main__":
    names = sorted({f.name.split("__")[0] for f in RUNS.glob("*__*.json")})
    print("conditions stored:", names)
    parts = {}
    for n in names:
        rows, sc, _ = R.condition_rows(n.replace("ladder_", "ladder:").replace("ctrl_", "ctrl:").replace("final_", "final:"))
        parts[n] = (rows, sc)
    json.dump({n: dict(rows=r, score=s) for n, (r, s) in parts.items()}, open(HERE / "summary.json", "w"), indent=1, default=float)
    print(json.dumps({n: (s and {k: s[k] for k in ("a_pass", "b_pass", "c_pass", "gain_Q", "gain_MI")}) for n, (r, s) in parts.items()}, indent=1, default=float))
