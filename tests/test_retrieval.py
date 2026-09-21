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


def test_c5_reconstructed_fraction_labels_spikes_by_their_own_currents():
    from types import SimpleNamespace
    from neurotape.recall.provenance import reconstructed_fraction
    res = SimpleNamespace(spikes_e=(np.zeros(4, int), np.array([0.1, 0.2, 1.1, 1.2])), spike_Iff=np.array([9., 1., 9., 9.]), spike_Irec=np.array([1., 9., 1., 1.]))
    assert reconstructed_fraction(res, 0.0, 1.0)["reconstructed_fraction"] == 0.5
    assert reconstructed_fraction(res, 1.0, 2.0)["reconstructed_fraction"] == 0.0
    assert np.isnan(reconstructed_fraction(res, 5.0, 6.0)["reconstructed_fraction"])
    assert reconstructed_fraction(SimpleNamespace(spike_Iff=None), 0, 1)["available"] is False


def _subprocess_hashes(code: str) -> dict:
    import json, os, subprocess, sys
    pre = ("import json,hashlib,numpy as np\nfrom neurotape.config import Config\nfrom neurotape.frontend.io import synthetic_streams\n"
           "from neurotape.network import build_inputs, simulate\n"
           "def base():\n c=Config(); c.frontend.kind='filterbank'; c.network.n_exc=80; c.network.n_inh=20\n"
           " c.protocol.encode_s=2.0; c.protocol.recall_delays_s=[0.5]; c.protocol.recall_s=1.5; return c\n"
           "def run(c):\n r=simulate(c, build_inputs(synthetic_streams(1,2.0),c)); return r, hashlib.md5(np.round(r.spikes_e[1],6).tobytes()).hexdigest()\nout={}\n")
    res = subprocess.run([sys.executable, "-c", pre + code + "\nprint(json.dumps(out))"], capture_output=True, text=True, env=dict(os.environ, PYTHONHASHSEED="0"))
    assert res.returncode == 0, res.stderr[-1500:]
    return json.loads(res.stdout.strip().splitlines()[-1])


@pytest.mark.slow
def test_c5_logging_provenance_does_not_change_a_single_spike():
    h = _subprocess_hashes("c=base(); out['off']=run(c)[1]\nc=base(); c.sim.log_provenance=True; r,hh=run(c); out['on']=hh; out['n']=int(r.spike_Iff.size); out['ns']=int(r.spikes_e[1].size)")
    assert h["on"] == h["off"] and h["n"] == h["ns"] > 0


def test_c6_frozen_read_is_labelled_non_biological_and_gates_write_and_capture():
    assert stc.plastic_model(Config()) == stc.PLASTIC_MODEL
    c = Config(); c.eval.freeze_plasticity_at_recall = True
    text = stc.plastic_model(c)
    assert "pgate = pl_t(t) : 1" in text and "dz/dt = pl_t(t)*(" in text
    assert "not biology" in type(c.eval).__doc__.lower()


@pytest.mark.slow
def test_c6_weights_do_not_move_during_a_frozen_recall_but_do_during_a_plastic_one():
    code = ("for k,fz in (('plastic',False),('frozen',True)):\n c=base(); c.protocol.recall_mode='cue'; c.protocol.cue_fraction=0.5; c.plasticity.noise=False\n"
            " c.eval.freeze_plasticity_at_recall=fz; c.sim.weight_log_dt_s=0.25; r,_=run(c); seg=r.timeline.recalls()[0]\n"
            " a=int(np.searchsorted(r.w_t, seg.t0)); b=int(np.searchsorted(r.w_t, seg.t1))-1\n"
            " d=r.h_log[:,b]-r.h_log[:,a]; decay=(1-r.h_log[:,a])*(1-np.exp(-(r.w_t[b]-r.w_t[a])*0.1/(688.4/60)))\n"
            " out[k]=float(np.abs(d-decay).max()); out[k+'_z']=float(np.abs(r.z_log[:,b]-r.z_log[:,a]).max())")
    h = _subprocess_hashes(code)
    assert h["frozen"] < 1e-6 and h["frozen_z"] < 1e-12          # only passive decay moves the weights
    assert h["plastic"] > 100 * max(h["frozen"], 1e-9)           # the ordinary read rewrites them


def test_c8_timeline_k1_is_the_base_timeline_and_k4_adds_cycles():
    from neurotape.recall.protocol import build_timeline
    base = Config(); base.protocol.encode_s = 4.0; base.protocol.recall_delays_s = [1.0]
    on1 = base.model_copy(deep=True); on1.mechanisms.iterative_settling = True                 # K = 1
    a, b = build_timeline(base), build_timeline(on1)
    assert [(s.name, s.t0, s.t1, s.cue_onsets) for s in a.segments] == [(s.name, s.t0, s.t1, s.cue_onsets) for s in b.segments]
    assert not on1.settling_active                                                            # K = 1 -> no projection is built
    k4 = on1.model_copy(deep=True); k4.settling.k_cycles = 4
    seg = build_timeline(k4).recalls()[0]
    assert len(seg.cue_onsets) == 4 and np.allclose(np.diff(seg.cue_onsets), seg.period_s) and seg.dur >= 4 * seg.period_s
    with pytest.raises(Exception):
        Config.model_validate({"settling": {"k_cycles": 4}})                                   # needs the switch


def test_c8_classification_of_a_settling_run():
    from neurotape.recall.settling import classify
    row = lambda own, fmax, rate: dict(own=own, foreign_max=fmax, rate_hz=rate)
    assert classify([row(0.1, 0.2, 1), row(0.2, 0.2, 1), row(0.4, 0.2, 1)]) == "converging"
    assert classify([row(0.2, 0.2, 1), row(0.1, 0.3, 1), row(0.0, 0.5, 1)]) == "confabulating"   # settling onto a FOREIGN stream
    assert classify([row(0.1, 0.1, 2), row(0.1, 0.1, 15), row(0.1, 0.1, 60)]) == "runaway"
    assert classify([row(0.1, 0.1, 1)]) == "flat" and classify([row(0.1, 0.2, 1), row(0.1, 0.2, 1)]) == "flat"


@pytest.mark.slow
def test_c8_k1_reproduces_exactly_and_the_learned_projection_changes_recall_not_a_random_one():
    code = ("c=base(); c.protocol.recall_mode='cue'; c.protocol.cue_fraction=0.25; out['base']=run(c)[1]\n"
            "c1=base(); c1.protocol.recall_mode='cue'; c1.protocol.cue_fraction=0.25; c1.mechanisms.iterative_settling=True; out['k1']=run(c1)[1]\n"
            "c4=c1.model_copy(deep=True); c4.settling.k_cycles=3; c4.protocol.cue_channel_fraction=0.5; c4.sim.log_provenance=True\n"
            "r,h=run(c4); out['k3']=h; seg=r.timeline.recalls()[0]; out['n_cycles']=len(seg.cue_onsets); out['views']=len(r.extra['cue_views'])\n"
            "out['fb_learned_max']=float(r.extra['fb_learned'].max()); out['fb_learned_min']=float(r.extra['fb_learned'].min())\n"
            "mv=c4.model_copy(deep=True); mv.settling.multi_view=True; r2,_=run(mv); v=r2.extra['cue_views']; out['views_differ']=bool(len(set(map(tuple,v)))>1); out['view_sizes']=[len(x) for x in v]")
    h = _subprocess_hashes(code)
    assert h["k1"] == h["base"]                                  # K = 1 equals current behaviour EXACTLY
    assert h["k3"] != h["base"] and h["n_cycles"] == 3
    assert h["views_differ"] and len(set(h["view_sizes"])) == 1  # C8b: rotating views, same fraction each cycle
    assert h["fb_learned_min"] >= -1.0                           # the projection's delivered weight is its LEARNED part only


def test_c7_experiment_is_blocked_by_the_operators_precondition_and_its_condition_count_is_fixed(monkeypatch):
    from neurotape.experiments import suite
    monkeypatch.delenv("NEUROTAPE_ALLOW_COMPLETION", raising=False)
    with pytest.raises(SystemExit) as e:
        suite.exp_completion(Config(), [0], 1)
    assert "0 of 18" in str(e.value)
    conds = suite.completion_conditions(Config())
    assert len(conds) == 4 * 4 + 3 * 3 + 3 * 2 == 31                       # fractions x K, multi-view variants, repeats x {plastic, frozen}
    assert all(not c.settling_active or c.protocol.cued for c in conds.values())
    assert conds["repeat x3 | FROZEN read (non-biological)"].protocol.recall_delays_s == [5.0] * 3
