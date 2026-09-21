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
