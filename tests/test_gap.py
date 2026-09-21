"""Gap junctions: measured coupling coefficient, and low-pass behaviour."""
import numpy as np
import brian2 as b2
from brian2 import ms, pA, mV, second

from neurotape.coupling.gap import conductance_for_cc, make_gap, ring_pairs
from conftest import quiet_cfg, single_cell


def _pair(cfg, cc):
    g = single_cell(cfg, n=2, kind="inh")
    syn = make_gap(g, [(0, 1)], conductance_for_cc(cc, cfg.network.inh.gL_nS), cfg.gap.modulation, "gap")
    return g, syn


def test_measured_coupling_coefficient():
    cfg = quiet_cfg()
    g, syn = _pair(cfg, 0.10)
    m = b2.StateMonitor(g, "V", record=True, dt=1 * ms); net = b2.Network(g, syn, m)
    net.run(200 * ms); v0 = np.array(m.V[:, -1] / mV)
    g.I_inj[0] = -100 * pA; net.run(400 * ms); v1 = np.array(m.V[:, -1] / mV)
    cc = (v1[1] - v0[1]) / (v1[0] - v0[0])
    assert 0.05 <= cc <= 0.15, cc
    assert abs(cc - 0.10) < 0.02


def test_modulation_scalar_scales_coupling():
    cfg = quiet_cfg(); cfg.gap.modulation = 0.0
    g, syn = _pair(cfg, 0.10)
    m = b2.StateMonitor(g, "V", record=True, dt=1 * ms); net = b2.Network(g, syn, m)
    net.run(100 * ms); g.I_inj[0] = -100 * pA; net.run(300 * ms)
    assert abs(m.V[1, -1] - m.V[1, 99]) < 0.01 * mV               # pH/Mg-like scalar at 0 = uncoupled


def test_low_pass_fast_attenuated_more_than_slow():
    ratios = {}
    for f in (2.0, 100.0):
        b2.start_scope()
        cfg = quiet_cfg(); g, syn = _pair(cfg, 0.10)
        g.run_regularly(f"I_inj = int(i == 0)*60*pA*sin(2*pi*{f}*Hz*t)", dt=0.1 * ms)
        m = b2.StateMonitor(g, "V", record=True, dt=0.1 * ms); b2.Network(g, syn, m).run(1500 * ms)
        v = np.array(m.V / mV)[:, 5000:]
        ratios[f] = np.ptp(v[1]) / np.ptp(v[0])
    assert ratios[100.0] < 0.5 * ratios[2.0], ratios            # fast signals attenuated more than slow


def test_ring_pairs_are_local_and_unique():
    pairs = ring_pairs(50, 8, 0.3, np.random.default_rng(0))
    assert len(set(map(frozenset, pairs))) == len(pairs)
    assert all(min((a - b) % 50, (b - a) % 50) <= 8 for a, b in pairs)
    assert 0.2 < len(pairs) / (50 * 8) < 0.4
