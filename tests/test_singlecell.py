"""Single-cell (Stentor) models. The first block is the REPRODUCTION GATE: with the published parameters and
switches off, the reimplementation must show every model behaviour Rajan & Marshall 2025 report (their Figs 2-7).
Nothing in E03 may run unless these pass. Forces: low 1.0, high 4.0 (their units; not printed for the figures)."""
import numpy as np
import pytest

from neurotape.singlecell import gate, sim
from neurotape.singlecell.models import CellConfig

L, H = 1.0, 4.0
PUB = CellConfig()


def pr(r, kind=None):
    return [e["p_response"] for e in r["events"] if kind is None or e["kind"] == kind]


# ------------------------------------------------------------------ reproduction gate (published model, unmodified)
def test_published_constants():
    assert PUB.params.S_star == pytest.approx(35.0)
    assert PUB.params.n_min == pytest.approx(12.0, abs=1e-3)


@pytest.mark.parametrize("name", list(gate.CHECKS))
def test_reproduction_gate(name):
    res = gate.CHECKS[name](PUB)
    assert res["ok"], res


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


def test_new_switches_default_to_the_published_model():
    from neurotape.singlecell.models import antimony
    assert CellConfig().rates == dict(k_syn=0.7, k_deg=0.02, k_rec=0.1, k_des=0.005)
    assert "X" not in antimony(CellConfig())
    a = sim.run(PUB, sim.sequence([(L, 1, 30), (0, 1, 30)]), probe_force=L)
    b = sim.run(CellConfig(recycling="constitutive", k_deg_scale=1.0), sim.sequence([(L, 1, 30), (0, 1, 30)]),
                probe_force=L)
    assert pr(a) == pr(b)


def test_labile_factor_only_moves_under_a_block():
    lab = sim.run(CellConfig(recycling="labile"), sim.sequence([(L, 1, 30)]), t_end=60)
    assert min(lab["trace"]["X"]) == pytest.approx(1.0)
    # same dynamics; the extra species changes the integrator's step control (differences ~1e-5)
    assert pr(lab) == pytest.approx(pr(sim.run(PUB, sim.sequence([(L, 1, 30)]))), rel=1e-4)
    blk = sim.run(CellConfig(recycling="labile", synthesis_scale=0.0), [], t_end=120)
    assert blk["trace"]["X"][-1] == pytest.approx(np.exp(-120 / 60), rel=1e-3)


def test_k_deg_scale_keeps_the_steady_state():
    cfg = CellConfig(k_deg_scale=0.01, synthesis_scale=0.0)
    r = sim.run(cfg, [sim.Stim(600, 0, L, "probe")])
    assert r["events"][0]["S_before"] == pytest.approx(35 * np.exp(-0.0002 * 600), rel=1e-3)
