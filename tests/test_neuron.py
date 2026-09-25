"""Single-cell physiology. g_T and hT_loaded are set by THESE tests and by nothing else."""
import itertools

import numpy as np
from brian2 import second

from neurotape.neurons.model import LOADED, REST, RESET, SPIKE, annotate_bursts
from conftest import quiet_cfg, step_protocol


def test_single_spikes_from_rest():
    """A depolarising step from rest gives isolated, adapting spikes -- never a burst."""
    sp, st, _ = step_protocol(quiet_cfg(), hyp_ms=0, dep_pA=250.0)
    t = np.array(sp.t / second)
    assert t.size >= 2
    assert np.diff(t).min() > 0.020
    assert annotate_bursts(t) == []
    assert np.all(np.diff(np.diff(t)) > 0) or t.size < 3          # spike-frequency adaptation


def test_rebound_burst_after_100ms_hyperpolarisation():
    sp, st, t_rel = step_protocol(quiet_cfg(), hyp_ms=100)
    t = np.array(sp.t / second)
    bursts = annotate_bursts(t)
    assert len(bursts) == 1 and bursts[0][2] >= 3
    assert 0 < bursts[0][0] - t_rel < 0.100                        # it is a REBOUND: no current is injected
    assert (np.asarray(st.nstate[0]) == LOADED).sum() > 20        # LOADED before release ...
    k_rel = int(t_rel * 1e3)
    assert np.asarray(st.nstate[0])[k_rel - 1] == LOADED


def test_no_rebound_without_t_current():
    cfg = quiet_cfg(); cfg.mechanisms.t_current = False
    sp, st, _ = step_protocol(cfg, hyp_ms=100)
    assert sp.num_spikes == 0


def test_burst_probability_increases_with_hyperpolarisation_duration():
    """With membrane noise, P(rebound burst) rises monotonically-ish with prior hyperpolarisation."""
    probs = []
    for hyp in (20, 50, 100, 200):
        cfg = quiet_cfg(); cfg.noise.sigma_pA = 30.0
        sp, st, t_rel = step_protocol(cfg, hyp_ms=hyp, n=40, seed=hyp)
        tr = sp.spike_trains()
        probs.append(np.mean([any(b[0] > t_rel and b[2] >= 3 for b in annotate_bursts(np.array(tr[k] / second))) for k in range(40)]))
    assert probs[0] < 0.1 and probs[-1] > 0.8
    assert all(b >= a - 0.05 for a, b in itertools.pairwise(probs))
    assert probs[-1] - probs[0] > 0.7


def test_state_enum_sequence():
    sp, st, _ = step_protocol(quiet_cfg(), hyp_ms=0, dep_pA=250.0)
    s = np.asarray(st.nstate[0])
    assert set(np.unique(s)) <= {REST, LOADED, SPIKE, RESET}
    k = np.flatnonzero(s == SPIKE)
    assert k.size and all(s[j + 1] == RESET for j in k if j + 1 < s.size and s[j + 1] != SPIKE)
    assert s[0] == REST


def test_tonic_drift_is_slow_ou():
    import brian2 as b2
    from conftest import single_cell
    cfg = quiet_cfg(); cfg.mechanisms.tonic_drift = True; cfg.drift.tau_s = 0.5; cfg.drift.sigma_pA = 20.0
    g = single_cell(cfg, n=200); m = b2.StateMonitor(g, "I_drift", record=True, dt=10 * b2.ms)
    b2.Network(g, m).run(3 * b2.second)
    x = np.asarray(m.I_drift / b2.pA)[:, 100:]
    assert abs(x.std() - 20.0) < 4.0                              # stationary SD = sigma
    # ENSEMBLE autocorrelation across cells (a per-cell estimate over 4 tau is biased far negative)
    ac = np.mean([np.corrcoef(x[:, k], x[:, k + 50])[0, 1] for k in range(0, 150, 10)])  # lag = tau -> ~1/e
    assert 0.2 < ac < 0.55


def test_nm_excitability_drive_raises_spiking_in_e_cells_only_and_is_absent_when_off():
    """Recall-phase drive candidate 1: same current step, more spikes under elevated NM; nothing when off."""
    import brian2 as b2
    from neurotape.neurons.model import make_group, constant_array, equations
    assert "ahp_scale" not in equations(False) and "- w - I_T" in equations(False)      # OFF = the original text
    counts = {}
    for label, on, nm, kind in (("off_hi", False, 0.42, "exc"), ("on_ref", True, 0.12, "exc"), ("on_hi", True, 0.42, "exc"), ("inh_on_hi", True, 0.42, "inh")):
        b2.start_scope()
        cfg = quiet_cfg(); cfg.mechanisms.nm_excitability = on; cfg.mechanisms.nm_inhibitory_setpoint = False
        p = cfg.network.exc if kind == "exc" else cfg.network.inh
        g = make_group(1, p, cfg, kind, constant_array(nm), constant_array(1.0), "c", np.random.default_rng(0)); g.V = p.EL_mV * b2.mV
        sp = b2.SpikeMonitor(g); net = b2.Network(g, sp); g.I_inj = 250 * b2.pA; net.run(500 * b2.ms); counts[label] = sp.num_spikes
    assert counts["on_hi"] > counts["off_hi"]                   # NM raises excitation-spike coupling
    assert counts["on_ref"] == counts["off_hi"]                 # neutral at the reference NM level
    b2.start_scope()
    cfg = quiet_cfg(); cfg.mechanisms.nm_inhibitory_setpoint = False
    g = make_group(1, cfg.network.inh, cfg, "inh", constant_array(0.42), constant_array(1.0), "c", np.random.default_rng(0)); g.V = -70 * b2.mV
    sp = b2.SpikeMonitor(g); g.I_inj = 250 * b2.pA; b2.Network(g, sp).run(500 * b2.ms)
    assert sp.num_spikes == counts["inh_on_hi"]                 # I cells never get the drive
