"""EXPLORATORY / PILOT -- not preregistered evidence. Smoke test of run.job() on OFF-LIST seed 900 before the
-prereg tag: does every arm and variant run and return every field? It prints run status, timing and the keys
returned, and deliberately NOT the outcome values. Outputs stay under exploratory/pilot/ (PREREG section 8)."""
import json, sys, time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
E = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(E))
import run as R

OUT = Path(__file__).resolve().parent


def _job(j):
    R.HERE = OUT                                   # stimuli.json read from the pilot folder, not outputs/
    t = time.time(); r = R.job(j); r["_s"] = time.time() - t
    return r


if __name__ == "__main__":
    (OUT / "outputs/stimuli").mkdir(parents=True, exist_ok=True)   # regenerated each run; not committed (the pre-prereg guard blocks outputs/)
    (OUT / "config.yaml").write_text((E / "config.yaml").read_text())
    st = R._stim_job(900)
    (OUT / "outputs/stimuli/stimuli.json").write_text(json.dumps({"900": st}, default=float))
    c = R.load_cfg()
    jobs = [dict(arm=a, schedule=s, seed=900, variant=v) for a in ("A", "H", "B", "Z", "G")
            for s in ("massed", "spaced") for v in [dict(name="base")]]
    jobs += [dict(arm="R", schedule=s, seed=900, variant=v) for s in ("massed", "spaced") for v in c["arms"]["R"]["variants"]]
    with ProcessPoolExecutor(8, mp_context=get_context("spawn")) as ex:
        res = list(ex.map(_job, jobs))
    for r in res:
        keys = sorted(r["probes"][0]) if r["ok"] else r.get("error")
        print(r["arm"], r["schedule"], r["variant"], "ok" if r["ok"] else "FAILED", f"{r['_s']:.0f}s", keys if not r["ok"] else len(keys))
    (OUT / "smoke_status.json").write_text(json.dumps([{k: r[k] for k in ("arm", "schedule", "variant", "ok", "_s")} |
                                                        ({"error": r["error"], "trace": r["trace"]} if not r["ok"] else {})
                                                        for r in res], indent=1))
