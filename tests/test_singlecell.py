"""Single-cell (Stentor) models. The first block is the REPRODUCTION GATE: with the published parameters and
switches off, the reimplementation must show every model behaviour Rajan & Marshall 2025 report (their Figs 2-7).
Nothing in E03 may run unless these pass. Forces: low 1.0, high 4.0 (their units; not printed for the figures)."""
import numpy as np
import pytest

from neurotape.singlecell import sim
from neurotape.singlecell.models import CellConfig

L, H = 1.0, 4.0
PUB = CellConfig()


def pr(r, kind=None):
    return [e["p_response"] for e in r["events"] if kind is None or e["kind"] == kind]


# ------------------------------------------------------------------ reproduction gate (published model, unmodified)
def test_published_constants():
    assert PUB.params.S_star == pytest.approx(35.0)
    assert PUB.params.n_min == pytest.approx(12.0, abs=1e-3)


def test_R1_habituation_then_recovery():
    p = pr(sim.run(PUB, sim.sequence([(L, 1, 60), (0, 1, 60)]), probe_force=L))
    assert p[59] < 0.5 * p[0]                      # decrement
    assert p[119] > p[59] + 0.3                     # recovery once stimuli stop


def test_R2_no_dishabituation():
    p = pr(sim.run(PUB, sim.sequence([(L, 1, 30), (H, 1, 1), (L, 1, 5)])))
    assert max(p[31:36]) <= p[29] + 1e-9            # a strong stimulus does not restore the weak response


def test_R3_force_dependence():
    lo = pr(sim.run(PUB, sim.sequence([(L, 1, 60)])))
    rh = sim.run(PUB, sim.sequence([(H, 1, 60)]))
    hi = pr(rh)
    assert lo[-1] / lo[0] < 0.5 and hi[-1] / hi[0] > 0.8
    assert rh["trace"]["S0"][-1] < sim.run(PUB, sim.sequence([(L, 1, 60)]))["trace"]["S0"][-1]   # hidden loss


def test_R4_hidden_variable_high_then_low():
    after = pr(sim.run(PUB, sim.sequence([(H, 1, 19), (L, 1, 41)])))[19]
    naive = pr(sim.run(PUB, sim.sequence([(L, 1, 1)])))[0]
    assert after < 0.5 * naive


def test_R5_interleaved_weak_habituates_strong_does_not():
    ev = [sim.Stim(k + 1, 0, L if k % 2 == 0 else H) for k in range(60)]
    p = pr(sim.run(PUB, ev))
    assert p[-2] < 0.5 * p[0] and p[-1] > 0.8 * p[1]


def test_R6_subliminal_accumulation_slows_recovery():
    def half(N):
        p = pr(sim.run(PUB, sim.sequence([(L, 1, N), (0, 1, 120)]), probe_force=L))[N:]
        base = pr(sim.run(PUB, sim.sequence([(0, 1, 1)]), probe_force=L))[0]
        thr = p[0] + 0.5 * (base - p[0])
        return next(i for i, x in enumerate(p) if x >= thr)
    assert half(200) > half(20)


def test_R7_frequency_dependence():
    last = [pr(sim.run(PUB, sim.sequence([(L, per, 60)]), sample_dt=min(per, 0.25)))[-1] for per in (0.02, 1, 5)]
    assert last[0] < last[1] < last[2]


def test_R8_no_rate_sensitivity():
    """Recovery is NOT faster after high-frequency training (the model shows a slight slowing; Stentor showed none)."""
    def half(per):
        seq = sim.sequence([(L, per, 60)]) + sim.sequence([(0, 1, 120)], t0=60 * per)
        p = pr(sim.run(PUB, seq, probe_force=L, sample_dt=min(per, 0.25)))[60:]
        base = pr(sim.run(PUB, sim.sequence([(0, 1, 1)]), probe_force=L))[0]
        thr = p[0] + 0.5 * (base - p[0])
        return next(i for i, x in enumerate(p) if x >= thr)
    assert half(0.02) >= half(1)


# ------------------------------------------------------------------ switches (defaults = published)
def test_one_channel_internalisation_is_the_published_model():
    a = sim.run(PUB, sim.sequence([(L, 1, 30)]))
    b = sim.run(CellConfig(n_channels=1, mechanism="internalisation", synthesis_scale=1.0), sim.sequence([(L, 1, 30)]))
    assert pr(a) == pr(b)


def test_two_channels_are_independent_pools():
    cfg = CellConfig(n_channels=2)
    seq = sim.sequence([(L, 1, 60)], channel=0) + [sim.Stim(61, 1, L, "probe")]
    r = sim.run(cfg, seq)
    naive = pr(sim.run(PUB, sim.sequence([(L, 1, 1)])))[0]
    assert r["events"][-1]["p_response"] == pytest.approx(naive, rel=1e-6)   # channel B untouched by A's training


def test_synthesis_block_changes_only_supply():
    blk = CellConfig(synthesis_scale=0.0)
    r = sim.run(blk, [sim.Stim(90, 0, L, "probe")])
    assert r["events"][0]["S_before"] == pytest.approx(35 * np.exp(-0.02 * 90), rel=1e-3)


def test_gating_variant_conserves_receptors_except_basal_turnover():
    g = CellConfig(mechanism="gating")
    r = sim.run(g, sim.sequence([(L, 1, 60)]), t_end=60)
    tot = r["trace"]["S0"][-1] + r["trace"]["I0"][-1]
    assert tot == pytest.approx(35.0, rel=1e-3)     # nothing destroyed; synthesis balances basal turnover


def test_sample_responses_is_seeded():
    r = sim.run(PUB, sim.sequence([(L, 1, 20)]))
    assert sim.sample_responses(r, 3) == sim.sample_responses(r, 3)
