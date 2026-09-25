"""Shared experiment plumbing: one worker = one (config, seed) run; aggregation = mean +/- 95% CI.

Every experiment writes to results/<timestamp>_<name>/ : config.yaml, runs.json (every seed, never
only the aggregate), summary.json, figures with the time-compression factor printed on them, and
REPORT.md. A condition that fails to beat its ablation or the reservoir is reported as failing.
"""
from __future__ import annotations

import json
import traceback
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from multiprocessing import get_context
from pathlib import Path

import numpy as np
from scipy import stats

from ..config import Config, dump_config

ROOT = Path(__file__).resolve().parents[3]


def results_dir(name: str) -> Path:
    d = ROOT / "results" / f"{datetime.now():%Y%m%d-%H%M%S}_{name}"  # noqa: DTZ005 -- a local-time folder name, never compared
    d.mkdir(parents=True, exist_ok=True)
    return d


def ci95(values) -> dict:
    v = np.asarray([x for x in values if x is not None and np.isfinite(x)], dtype=float)
    if v.size == 0:
        return dict(mean=float("nan"), lo=float("nan"), hi=float("nan"), n=0)
    if v.size == 1:
        return dict(mean=float(v[0]), lo=float("nan"), hi=float("nan"), n=1)
    h = stats.t.ppf(0.975, v.size - 1) * v.std(ddof=1) / np.sqrt(v.size)
    return dict(mean=float(v.mean()), lo=float(v.mean() - h), hi=float(v.mean() + h), n=int(v.size))


def fmt(c: dict) -> str:
    return f"{c['mean']:+.3f} [{c['lo']:+.3f}, {c['hi']:+.3f}] (n={c['n']})"


def paired_diff(a, b) -> dict:
    """a - b per seed, with a 95% CI. 'beats' is claimed only if the whole CI is above zero.

    a and b must be the SAME seeds in the same order. Pairing is by position, so unequal lengths now raise
    (they used to be truncated, which silently misaligns every later pair if one condition lost a seed). Equal
    lengths with different failed seeds would still misalign; callers pass runs from by_tag, and no committed
    result had a failed seed in a paired condition (docs/REVIEW.md)."""
    if len(a) != len(b):
        raise ValueError(f"paired_diff: {len(a)} vs {len(b)} values -- a failed seed would misalign the pairing")
    c = ci95(np.asarray(a, float) - np.asarray(b, float))
    c["beats"] = bool(np.isfinite(c["lo"]) and c["lo"] > 0)
    return c


def get_streams(spec: dict, cfg: Config):
    from ..frontend.io import load_streams, synthetic_streams
    if spec.get("files"):
        return load_streams(spec["files"], cfg.frontend.csv_rate_hz)
    # A DIFFERENT stimulus per seed. With one shared stimulus the seeds are not independent: anything
    # locked to recall onset correlates with the same envelope every time and the CI comes out falsely tight.
    return synthetic_streams(spec.get("n", 1), cfg.protocol.encode_s, seed=spec.get("stream_seed", cfg.seed))


def run_one(job: dict) -> dict:
    """Worker. job = {cfg: dict, streams: spec, tag: str, esn: bool, raw: bool}."""
    try:
        from ..network import build_inputs, simulate
        from ..recall.evaluate import evaluate
        from ..decode import baselines, readout as ro
        cfg = Config.model_validate(job["cfg"])
        streams = get_streams(job["streams"], cfg)
        inputs = build_inputs(streams, cfg)
        res = simulate(cfg, inputs)
        out, _ = evaluate(res, inputs, cfg)
        if job.get("esn") or job.get("raw"):
            Y = ro.resample_targets(inputs.env, inputs.env_rate, cfg.decode.rate_hz)
            if job.get("esn"):
                out["esn"] = baselines.esn_evaluate(inputs, res.timeline, cfg, Y, cfg.seed)
            if job.get("raw"):
                out["raw_input_r"] = baselines.raw_input_upper_bound(inputs, cfg, Y)
        out.update(tag=job["tag"], seed=cfg.seed, ok=True,
                   input_log={k: v for k, v in inputs.log.items() if k != "projection"})
        return out
    except Exception as e:                                   # a failed seed is reported, never dropped
        return dict(tag=job.get("tag"), seed=job["cfg"].get("seed"), ok=False,
                    error=f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-1500:])


def run_jobs(jobs: list[dict], n_workers: int) -> list[dict]:
    if n_workers <= 1:
        return [run_one(j) for j in jobs]
    with ProcessPoolExecutor(n_workers, mp_context=get_context("spawn")) as ex:
        return list(ex.map(run_one, jobs))


def jobs_for(conditions: dict[str, Config], seeds, streams: dict, **flags) -> list[dict]:
    jobs = []
    for tag, cfg in conditions.items():
        for s in seeds:
            c = cfg.model_copy(deep=True); c.seed = int(s)
            jobs.append(dict(cfg=c.model_dump(), streams=streams, tag=tag, **flags))
    return jobs


def by_tag(runs: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in runs:
        if r.get("ok"):
            out.setdefault(r["tag"], []).append(r)
    for v in out.values():
        v.sort(key=lambda r: r["seed"])
    return out


def save(outdir: Path, cfg: Config, runs: list[dict], summary: dict, report: str) -> None:
    dump_config(cfg, outdir / "config.yaml")
    (outdir / "runs.json").write_text(json.dumps(runs, indent=1, default=float))
    (outdir / "summary.json").write_text(json.dumps(summary, indent=1, default=float))
    failed = [r for r in runs if not r.get("ok")]
    head = f"# {outdir.name}\n\n_{cfg.compression_label()}_\n\n"
    if failed:
        head += f"**{len(failed)} of {len(runs)} runs FAILED and are excluded:** " + \
                "; ".join(f"{r['tag']}/seed {r['seed']}: {r['error']}" for r in failed[:5]) + "\n\n"
    try:
        from ..monorepo import stamp
        (outdir / "provenance.json").write_text(json.dumps(stamp(
            ["tools/universal-wave-translation-layer", "tools/result-provenance"]), indent=1, default=str))
    except Exception as e:
        head += f"_provenance stamp unavailable: {e}_\n\n"
    (outdir / "REPORT.md").write_text(head + report)


def stamp_figure(fig, cfg: Config, extra: str = "") -> None:
    fig.text(0.5, 0.005, cfg.compression_label() + (" | " + extra if extra else ""),
             ha="center", va="bottom", fontsize=7, color="0.35")
