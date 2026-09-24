"""EXPLORATORY (post hoc, E01). Not preregistered, not cited as a preregistered result.

Question: is the NEGATIVE decrement SR2 found for `std` at slow periodic rates (0.01-0.1 Hz) an artefact of the
mean-field fast-forward used for gaps > 2 s? Same arm, stimulus and seeds as SR2, 0.1 Hz and 0.03 Hz periodic,
with the gaps (a) fast-forwarded exactly as run.py does and (b) simulated directly. Uses run.py's own functions.
"""
import json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import run as R  # noqa: E402

def one(seed, rate, direct):
    from neurotape.habituation.protocol import make_sim
    from neurotape.habituation.stimuli import family
    c = R.load_cfg(); cfg = R.arm_cfg(c, "std", seed)
    sim, st = make_sim(cfg); fam = family(seed, 0.2, 1, [])
    dt, steps = sim.dt, int(round(0.2 / sim.dt)); rng = np.random.default_rng(seed + 4242)
    out = []
    for k in range(16):
        rec = sim.present(st, fam.stored, rng)
        out.append(float(R.driven(rec, steps, sim.rate_e_spont, cfg.network.n_exc, dt)[0]))
        if k < 15:
            (sim.quiet if direct else sim.advance)(st, 1 / rate - 0.2, rng)
    out = np.array(out)
    return float(1 - out[-4:].mean() / out[0])

if __name__ == "__main__":
    res = {}
    for rate in (0.1, 0.03):
        for direct in (False, True):
            D = [one(s, rate, direct) for s in range(10)]
            res[f"{rate}|{'direct' if direct else 'fast-forward'}"] = dict(D=D, mean=float(np.mean(D)),
                                                                           sd=float(np.std(D, ddof=1)))
            print(rate, "direct" if direct else "fast-forward", f"mean D {np.mean(D):+.4f} sd {np.std(D, ddof=1):.4f}", flush=True)
    (HERE / "ff_vs_direct.json").write_text(json.dumps(res, indent=1))
