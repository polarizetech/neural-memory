"""model-v0.2.0 (E02) mechanisms: feedforward inhibition with iSTDP, receptor inactivation, the removal and
global-gain switches, per-cell recording, and the analytic receptor pools. Rate periphery, small network.
Nothing here reads a recognition or retention result."""
import numpy as np
import pytest
from pydantic import ValidationError

from neurotape.experiments.habituation import _merge
from neurotape.habituation import analytic as A
from neurotape.habituation.config import HabConfig
from neurotape.habituation.model import build_net, receptor_rates, run
from neurotape.habituation.protocol import make_sim
from neurotape.habituation.stimuli import family

SMALL = dict(periphery=dict(kind="rate", n_cf=16, relay_per_cf=4), network=dict(n_exc=60, n_inh=15))
FF = dict(on=True, n_ff=20)


def small(**over) -> HabConfig:
    return HabConfig.model_validate(_merge(SMALL, over))


def test_new_switches_validate():
    with pytest.raises(ValidationError):
        small(ffinh=dict(plastic=True, eta=0.01))                 # plastic needs on
    with pytest.raises(ValidationError):
        small(ffinh=dict(on=True, plastic=True, eta=0.0))          # would never learn
    with pytest.raises(ValidationError):
        small(receptor=dict(on=True, k_rate=1.0))                  # unknown key


def test_ff_pathway_does_not_touch_the_e_network_structure():
    from neurotape.habituation.periphery import Periphery
    c0, c1 = small(), small(ffinh=FF)
    cf = Periphery(c0).cf
    n0, n1 = build_net(c0, cf), build_net(c1, cf)
    for k in ("W0", "W_ei", "W_ie", "cf_e"):
        assert np.array_equal(getattr(n0, k), getattr(n1, k))
    assert n0.W_fe is None and n1.W_fe.shape == (20, 60)


def test_global_gain_of_one_is_bit_identical():
    sim, st = make_sim(small())
    fam = family(0, 0.5, 1, [])
    r = sim.raster(fam.stored, np.random.default_rng(1))
    a, b = st.copy(), st.copy()
    b.g_in = np.ones(1)
    ra = run(sim.net, a, r, np.random.default_rng(2))
    rb = run(sim.net, b, r, np.random.default_rng(2))
    assert np.array_equal(ra.e_count, rb.e_count) and np.array_equal(a.V, b.V)
    c = st.copy(); c.g_in = np.full(1, 0.5)
    rc = run(sim.net, c, r, np.random.default_rng(2))
    assert rc.e_count.sum() < ra.e_count.sum()


def test_removing_the_ff_pathway_disinhibits():
    """Removal is compared across two SEPARATE calls with the same noise seed (paired). Copies within one batch
    draw different membrane noise, so they are not paired."""
    sim, st = make_sim(small(ffinh=dict(FF, w_rf_nS=2.0, w_fe_nS=1.0)))
    fam = family(0, 0.5, 1, [])
    r = sim.raster(fam.stored, np.random.default_rng(1))
    on, off = st.copy(), st.copy()
    off.ff_out[:] = 0.0
    r_on = run(sim.net, on, r, np.random.default_rng(2))
    r_off = run(sim.net, off, r, np.random.default_rng(2))
    assert r_on.ff_count.sum() > 0 and np.array_equal(r_on.ff_count, r_off.ff_count)
    assert r_off.e_count.sum() > r_on.e_count.sum()


def test_keep_cells_matches_cell_count():
    sim, st = make_sim(small())
    fam = family(0, 0.5, 1, [])
    rec = run(sim.net, st, sim.raster(fam.stored, np.random.default_rng(1)), np.random.default_rng(2), keep_cells=True)
    assert np.array_equal(rec.cells_t.sum(0), rec.cell_count)


def test_istdp_learns_a_stimulus_specific_negative_image_and_relaxes():
    cfg = small(ffinh=dict(FF, plastic=True, eta=0.05, w_rf_nS=2.0, w_fe_nS=0.5))
    sim, st = make_sim(cfg)
    assert st.alpha is not None and st.alpha > 0
    fam = family(0, 1.0, 1, [])
    drive_e = sim.per.relay_rate(fam.stored).mean(0)               # (n_cf,) naive drive, per CF
    rng = np.random.default_rng(3)
    G0 = st.G.copy()
    for _ in range(8):
        sim.present(st, fam.stored, rng); sim.quiet(st, 1.0, rng)
    conn = sim.net.W_fe > 0
    dG = (st.G - G0)[0]
    # E cells nearest the stimulus's strongest CF vs the weakest: potentiation should favour the driven ones
    cf = sim.per.cf
    near = np.abs(np.log2(sim.net.cf_e / cf[np.argmax(drive_e)])) < 0.3
    far = np.abs(np.log2(sim.net.cf_e / cf[np.argmin(drive_e)])) < 0.3
    assert (dG[:, near][conn[:, near]]).mean() > (dG[:, far][conn[:, far]]).mean() + 1e-3
    a, b = st.copy(), st.copy()
    sim.fast_forward(a, 60.0)
    sim.quiet(b, 60.0, np.random.default_rng(4))
    assert np.abs(a.G - b.G)[0][conn].mean() < 0.01 * np.abs(st.G - cfg.ffinh.g0)[0][conn].mean() + 1e-3


def test_receptor_steady_state_and_fast_forward():
    cfg = small(depression=dict(on=False), receptor=dict(on=True, k_int=0.02))
    sim, st = make_sim(cfg)
    assert abs(st.Srec.mean() - 1.0) < 0.01
    s = st.copy(); s.Srec[:] = 0.7; s.Irec[:] = 0.3
    a, b = s.copy(), s.copy()
    sim.fast_forward(a, 60.0)
    sim.quiet(b, 60.0, np.random.default_rng(5))
    assert abs(a.Srec.mean() - b.Srec.mean()) < 0.01 and abs(a.Irec.mean() - b.Irec.mean()) < 0.01


def test_synthesis_block_drains_surface_at_basal_degradation():
    """With synthesis at 0 and I at steady state, the surface pool falls at about k_deg in silence."""
    cfg = small(depression=dict(on=False), receptor=dict(on=True, synthesis_scale=0.0))
    sim, st = make_sim(cfg)
    sim.fast_forward(st, 1800.0)
    rr = receptor_rates(cfg)
    assert st.Srec.mean() < np.exp(-rr["k_deg"] * 1800.0) + 0.05
    assert st.Srec.mean() < 0.8


def test_analytic_receptor_pools_match_the_simulator_in_silence():
    cfg = small(depression=dict(on=False), receptor=dict(on=True, k_int=0.02, synthesis_scale=0.25))
    sim, st = make_sim(cfg)
    n_cf = cfg.periphery.n_cf
    pools = A.naive_pools(cfg, n_cf)
    pools["S"][:] = 0.6; pools["I"][:] = 0.3
    st.Srec[:] = 0.6; st.Irec[:] = 0.3
    p1 = A.silence_pools(cfg, pools, 900.0)
    sim.fast_forward(st, 900.0)
    assert abs(p1["S"].mean() - st.Srec.mean()) < 1e-3
    assert abs(p1["I"].mean() - st.Irec.mean()) < 1e-3


def test_overlap_metric():
    a = np.array([[1.0, 5.0, 1.0, 1.0]])
    assert A.overlap(a, a, 1.0) == pytest.approx(1.0)
    assert A.overlap(a, np.array([[1.0, 1.0, 1.0, 5.0]]), 1.0) == pytest.approx(0.0)
