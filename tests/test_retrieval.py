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
