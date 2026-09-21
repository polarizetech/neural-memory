"""Retrieval-as-writing and iterative settling. Every switch: OFF = regression, ON = the expected direction."""
import hashlib

import numpy as np
import pytest
import brian2 as b2

from neurotape.config import Config
from neurotape.neurons import model as m
from neurotape.plasticity import stc
from conftest import quiet_cfg

H = lambda s: hashlib.sha256(s.encode()).hexdigest()[:16]
# Hashes of the equation text of the model the committed results came from (taken at commit ae42d41f).
PINNED = dict(neuron="8d970b980a3b0b21", reset="97867d4c3f6b24df", syn="fc55c0b58709fbf8", on_pre="1e3a563f8ef3960c", on_post="f672868e6262ae55")


def test_all_switches_off_is_the_published_model_text():
    cfg = Config()
    assert not any(getattr(cfg.mechanisms, k) for k in ("nm_excitability", "intrinsic_trace"))
    assert H(m.equations()) == PINNED["neuron"]
    assert H(m.RESET_CODE) == PINNED["reset"] and H(stc.PLASTIC_MODEL) == PINNED["syn"]
    assert H(str(sorted(stc.ON_PRE.items()))) == PINNED["on_pre"] and H(stc.ON_POST) == PINNED["on_post"]


def _spikes(cfg, creb, pA=250.0, ms=600):
    b2.start_scope()
    g = m.make_group(1, cfg.network.exc, cfg, "exc", m.constant_array(0.12), m.constant_array(1.0), "c", np.random.default_rng(0))
    g.V = -70 * b2.mV; g.creb = creb
    sp = b2.SpikeMonitor(g); net = b2.Network(g, sp); g.I_inj = pA * b2.pA; net.run(ms * b2.ms)
    return sp.num_spikes


def test_c1_intrinsic_trace_raises_excitability_with_the_trace_and_needs_creb():
    off, on = quiet_cfg(), quiet_cfg(); on.mechanisms.intrinsic_trace = True
    for c in (off, on):
        c.creb.tau_s = 1e9                                   # hold the trace where the test puts it
    assert _spikes(on, 0.0) == _spikes(off, 0.0)             # no trace -> no effect
    assert _spikes(on, 1.0) > _spikes(off, 1.0) >= _spikes(off, 0.0)   # trace -> less adaptation, lower threshold
    with pytest.raises(Exception):
        Config.model_validate({"mechanisms": {"intrinsic_trace": True, "creb": False}})


def _run_cell(cfg, creb0=0.5, ms=800, pA=300.0):
    b2.start_scope()
    g = m.make_group(1, cfg.network.exc, cfg, "exc", m.constant_array(0.12), m.constant_array(1.0), "c", np.random.default_rng(0))
    g.V = -70 * b2.mV; g.creb = creb0
    sp = b2.SpikeMonitor(g); st = b2.StateMonitor(g, "creb", record=True, dt=10 * b2.ms)
    net = b2.Network(g, sp, st); g.I_inj = pA * b2.pA; net.run(ms * b2.ms)
    return sp.num_spikes, float(st.creb[0][-1])


def test_c4_prior_drift_erodes_the_trace_per_spike_and_repulsion_raises_threshold():
    assert m.reset_code() == m.RESET_CODE                                  # off = the published reset text
    base, drift, rep = quiet_cfg(), quiet_cfg(), quiet_cfg()
    for c in (base, drift, rep):
        c.creb.tau_s = 1e9; c.creb.Ca_spike = 0.0                           # isolate: no growth, no slow decay
    drift.mechanisms.prior_drift = True; rep.mechanisms.prior_repulsion = True
    n0, c0 = _run_cell(base); n1, c1 = _run_cell(drift); n2, _ = _run_cell(rep)
    assert c0 == pytest.approx(0.5, abs=1e-6)                               # untouched without the switch
    # eroded once per spike, exactly (the 10 ms monitor can sit one spike behind the spike count)
    assert n1 > 0 and any(c1 == pytest.approx(0.5 * 0.99 ** k, rel=1e-4) for k in (n1, n1 - 1))
    assert n2 < n0                                                          # recent use -> harder to fire ("seek novel")


def _write_test(cfg, M=None, creb_post=0.0, z0=0.0, lab=None, ms=300):
    """Toy: one synapse held above the LTP calcium threshold. Does the early-phase weight h get WRITTEN?"""
    b2.start_scope(); b2.defaultclock.dt = 0.1 * b2.ms
    cfg.plasticity.noise = False
    grp = b2.NeuronGroup(2, "M_pop : 1\ncreb : 1\nlab : 1\nCaT : 1\np : 1\nsum_h_diff : 1\ng_e : siemens", name="toy")
    if M is not None: grp.M_pop = M
    grp.creb = creb_post
    if lab is not None: grp.lab = lab
    S = b2.Synapses(grp, grp, stc.plastic_model(cfg), method="heun", namespace=stc.namespace(cfg), dt=1 * b2.ms, name="toy_syn")
    S.connect(i=[0], j=[1]); S.h = 1.0; S.z = z0; S.Ca = 100.0                  # far above theta_p for the whole run
    b2.Network(grp, S).run(ms * b2.ms)
    return float(S.h[0]) - 1.0


def test_c2_mismatch_gate_three_regimes():
    assert stc.plastic_model(Config()) == stc.PLASTIC_MODEL                     # off = the published synapse text
    off = _write_test(Config()); assert off > 0.05                              # ungated: the synapse is written
    g = Config(); g.mechanisms.mismatch_gate = True
    assert _write_test(g, M=0.05) == pytest.approx(0.0, abs=1e-9)               # below theta_low: retrieval only
    assert _write_test(g, M=0.4) == pytest.approx(off, rel=1e-6)                # mid regime: plasticity open
    hi_no_bias = _write_test(g, M=0.9, creb_post=0.0); hi_bias = _write_test(g, M=0.9, creb_post=0.2)
    assert hi_no_bias == pytest.approx(0.0, abs=1e-9) and hi_bias == pytest.approx(off, rel=1e-6)   # new trace -> allocation-biased cells
    assert _write_test(g, M=0.9, creb_post=0.2, z0=0.5) == pytest.approx(0.0, abs=1e-9)             # existing assembly protected


def test_c2_mismatch_is_high_when_feedforward_dominates_and_low_when_balanced():
    b2.start_scope(); cfg = quiet_cfg(); cfg.mechanisms.mismatch_gate = True
    g = m.make_group(3, cfg.network.exc, cfg, "exc", m.constant_array(0.12), m.constant_array(1.0), "c", np.random.default_rng(0))
    g.V = -70 * b2.mV
    g.run_regularly("g_ext = ge_in; g_e = gr_in", dt=0.1 * b2.ms)
    g.namespace.update(ge_in=0 * b2.nS, gr_in=0 * b2.nS)
    st = b2.StateMonitor(g, "mism", record=True, dt=5 * b2.ms); net = b2.Network(g, st)
    out = []
    for ff, rec in ((2.0, 0.0), (1.0, 1.0), (0.0, 2.0)):
        g.namespace.update(ge_in=ff * b2.nS, gr_in=rec * b2.nS); net.run(400 * b2.ms); out.append(float(st.mism[0][-1]))
    assert out[0] > 0.9 and out[1] < 0.1 and out[2] > 0.9      # |ff - rec| normalised: input-only and recurrent-only both mismatch


def test_c3_lability_window_opens_on_a_recurrent_spike_closes_again_and_gains_the_write():
    assert "lab" not in m.reset_code() and m.reset_code(lability=True).endswith("int(rec_lp > ff_lp)")
    off = _write_test(Config())
    c = Config(); c.mechanisms.lability_window = True
    assert _write_test(c, lab=0.0) == pytest.approx(off, rel=1e-6)                 # closed window = ordinary plasticity
    assert _write_test(c, lab=1.0) > 1.5 * off                                     # open window = a gain on the write
    both = Config(); both.mechanisms.lability_window = True; both.mechanisms.mismatch_gate = True
    assert _write_test(both, M=0.4, lab=0.0) == pytest.approx(0.0, abs=1e-9)       # with the gate: mid regime writes ONLY the reactivated cells
    assert _write_test(both, M=0.4, lab=1.0) > 1.5 * off
    # the window itself: a spike under recurrent drive opens it, under feedforward drive does not, and it decays
    res = {}
    for label, ff, rec in (("recurrent", 0.0, 6.0), ("feedforward", 6.0, 0.0)):
        b2.start_scope(); cfg = quiet_cfg(); cfg.mechanisms.lability_window = True; cfg.lability.tau_s = 0.2
        g = m.make_group(1, cfg.network.exc, cfg, "exc", m.constant_array(0.12), m.constant_array(1.0), "c", np.random.default_rng(0)); g.V = -70 * b2.mV
        g.namespace.update(ge_in=ff * b2.nS, gr_in=rec * b2.nS); op = g.run_regularly("g_ext = ge_in; g_e = gr_in", dt=0.1 * b2.ms)
        sp = b2.SpikeMonitor(g); st = b2.StateMonitor(g, "lab", record=True, dt=5 * b2.ms); net = b2.Network(g, sp, st, op)
        net.run(400 * b2.ms); peak = float(st.lab[0].max()); g.namespace.update(ge_in=0 * b2.nS, gr_in=0 * b2.nS); net.run(1000 * b2.ms)
        res[label] = (sp.num_spikes, peak, float(st.lab[0][-1]))
    assert res["recurrent"][0] > 0 and res["recurrent"][1] > 0.9 and res["recurrent"][2] < 0.05     # opens, then restabilises
    assert res["feedforward"][0] > 0 and res["feedforward"][1] == 0.0                               # input-driven spikes do not open it
