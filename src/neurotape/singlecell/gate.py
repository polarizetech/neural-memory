"""The reproduction gate R1-R8: every model behaviour Rajan & Marshall 2025 report (their Figs 2-7), as checks that
take any CellConfig. The published model must pass all eight (tests/test_singlecell.py); E03 asks which variants
still do. Forces: low 1.0, high 4.0 (their units; the figures' values are not printed) [ARBITRARY]."""
from __future__ import annotations

from . import sim
from .models import CellConfig

L, H = 1.0, 4.0


def _pr(r, kind=None):
    return [e["p_response"] for e in r["events"] if kind is None or e["kind"] == kind]


def _half_recovery(cfg: CellConfig, per: float, n: int) -> int | None:
    seq = sim.sequence([(L, per, n)]) + sim.sequence([(0, 1, 120)], t0=n * per)
    p = _pr(sim.run(cfg, seq, probe_force=L, sample_dt=min(per, 0.25)))[n:]
    base = _pr(sim.run(cfg, sim.sequence([(0, 1, 1)]), probe_force=L))[0]
    thr = p[0] + 0.5 * (base - p[0])
    return next((i for i, x in enumerate(p) if x >= thr), None)


def R1(cfg):
    p = _pr(sim.run(cfg, sim.sequence([(L, 1, 60), (0, 1, 60)]), probe_force=L))
    return dict(ok=p[59] < 0.5 * p[0] and p[119] > p[59] + 0.3, first=p[0], after60=p[59], probe60=p[119])


def R2(cfg):
    p = _pr(sim.run(cfg, sim.sequence([(L, 1, 30), (H, 1, 1), (L, 1, 5)])))
    return dict(ok=max(p[31:36]) <= p[29] + 1e-9, before=p[29], after_max=max(p[31:36]))


def R3(cfg):
    rl = sim.run(cfg, sim.sequence([(L, 1, 60)]))
    rh = sim.run(cfg, sim.sequence([(H, 1, 60)]))
    lo, hi = _pr(rl), _pr(rh)
    ok = lo[-1] / lo[0] < 0.5 and hi[-1] / hi[0] > 0.8 and rh["trace"]["S0"][-1] < rl["trace"]["S0"][-1]
    return dict(ok=ok, low_ratio=lo[-1] / lo[0], high_ratio=hi[-1] / hi[0])


def R4(cfg):
    after = _pr(sim.run(cfg, sim.sequence([(H, 1, 19), (L, 1, 41)])))[19]
    naive = _pr(sim.run(cfg, sim.sequence([(L, 1, 1)])))[0]
    return dict(ok=after < 0.5 * naive, after=after, naive=naive)


def R5(cfg):
    p = _pr(sim.run(cfg, [sim.Stim(k + 1, 0, L if k % 2 == 0 else H) for k in range(60)]))
    return dict(ok=p[-2] < 0.5 * p[0] and p[-1] > 0.8 * p[1], low=(p[0], p[-2]), high=(p[1], p[-1]))


def R6(cfg):
    a, b = _half_recovery(cfg, 1, 20), _half_recovery(cfg, 1, 200)
    return dict(ok=a is not None and b is not None and b > a, half20=a, half200=b)


def R7(cfg):
    last = [_pr(sim.run(cfg, sim.sequence([(L, per, 60)]), sample_dt=min(per, 0.25)))[-1] for per in (0.02, 1, 5)]
    return dict(ok=last[0] < last[1] < last[2], last=last)


def R8(cfg):
    """Recovery is NOT faster after high-frequency training (the model shows a slight slowing; Stentor showed none)."""
    fast, slow = _half_recovery(cfg, 0.02, 60), _half_recovery(cfg, 1, 60)
    return dict(ok=fast is not None and slow is not None and fast >= slow, half_fast=fast, half_slow=slow)


CHECKS = dict(R1=R1, R2=R2, R3=R3, R4=R4, R5=R5, R6=R6, R7=R7, R8=R8)


def check(cfg: CellConfig) -> dict:
    return {k: f(cfg) for k, f in CHECKS.items()}
