import numpy as np
import pytest
import brian2 as b2
from brian2 import ms, mV, pA

from neurotape.config import Config
from neurotape.neurons.model import make_group, constant_array


@pytest.fixture(autouse=True)
def _runtime():
    b2.set_device("runtime"); b2.prefs.codegen.target = "numpy"; b2.start_scope()
    b2.defaultclock.dt = 0.1 * ms
    yield


def quiet_cfg(**exc) -> Config:
    cfg = Config(); cfg.noise.I0_pA = 0; cfg.noise.sigma_pA = 0; cfg.mechanisms.tonic_drift = False
    cfg.mechanisms.theta = False
    for k, v in exc.items():
        setattr(cfg.network.exc, k, v)
    return cfg


def single_cell(cfg, n=1, kind="exc", seed=0):
    p = cfg.network.exc if kind == "exc" else cfg.network.inh
    g = make_group(n, p, cfg, kind, constant_array(cfg.neuromod.nm_ref), constant_array(1.0), "cell", np.random.default_rng(seed))
    g.V = p.EL_mV * mV
    return g


def step_protocol(cfg, hyp_ms, hyp_pA=-250.0, dep_pA=0.0, after_ms=300.0, n=1, seed=0):
    g = single_cell(cfg, n=n, seed=seed)
    sp = b2.SpikeMonitor(g); st = b2.StateMonitor(g, ["V", "hT", "nstate"], record=True, dt=1 * ms)
    net = b2.Network(g, sp, st)
    net.run(100 * ms)
    if hyp_ms > 0:
        g.I_inj = hyp_pA * pA; net.run(hyp_ms * ms)
    g.I_inj = dep_pA * pA; net.run(after_ms * ms)
    return sp, st, (100 + hyp_ms) * 1e-3
