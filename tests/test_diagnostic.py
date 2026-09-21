"""Storage diagnostic: D1 NM gating, D2 weight snapshots, D3 dW stream decode."""
import numpy as np
import pytest
import brian2 as b2

from neurotape.config import Config
from neurotape.neurons import model as m
from conftest import quiet_cfg
from test_retrieval import H, PINNED, _subprocess_hashes


def test_d1_gate_is_identically_zero_outside_recall_and_text_is_unchanged_when_off():
    from neurotape.neuromod.nm import recall_gate, NM_DT_S
    from neurotape.recall.protocol import build_timeline
    cfg = Config(); tl = build_timeline(cfg); t = np.arange(0, tl.total_s, NM_DT_S); g = recall_gate(tl, t)
    enc = tl.segment("encode")
    assert np.all(g[(t >= 0) & (t < enc.t1)] == 0.0)                         # settle + encoding: identically zero
    assert all(np.all(g[(t >= s.t0) & (t < s.t1)] == (1.0 if s.kind == "recall" else 0.0)) for s in tl.segments)
    assert H(m.equations()) == PINNED["neuron"]                              # switch off: the published text
    assert m.equations(True) == m.equations(True, nm_recall_only=False)      # and the DRIVE text is unchanged too
    assert "nm_gate(t)" in m.equations(True, nm_recall_only=True) and "nm_gate" not in m.equations(False, nm_recall_only=True)


def test_d1_with_the_gate_closed_an_nm_burst_does_nothing_to_the_cell():
    def spikes(drive, gate):
        b2.start_scope(); cfg = quiet_cfg(); cfg.mechanisms.nm_excitability = drive; cfg.mechanisms.nm_recall_only = gate is not None
        g = m.make_group(1, cfg.network.exc, cfg, "exc", m.constant_array(0.42), m.constant_array(1.0), "c", np.random.default_rng(0),
                         nm_gate=None if gate is None else m.constant_array(gate)); g.V = -70 * b2.mV
        sp = b2.SpikeMonitor(g); st = b2.StateMonitor(g, "nm_x", record=True, dt=1 * b2.ms) if drive else None
        net = b2.Network(*(o for o in (g, sp, st) if o is not None)); g.I_inj = 250 * b2.pA; net.run(500 * b2.ms)
        return sp.num_spikes, (None if st is None else float(np.abs(st.nm_x[0]).max()))
    off, _ = spikes(False, None); closed, x0 = spikes(True, 0.0); opened, x1 = spikes(True, 1.0)
    assert x0 == 0.0 and closed == off                                       # gate closed: the NM term is identically zero
    assert x1 > 0.2 and opened > off                                         # gate open: the drive acts


@pytest.mark.slow
def test_d2_snapshots_are_taken_at_the_three_instants_and_change_no_spike():
    code = ("c=base(); c.protocol.recall_mode='cue'; out['off']=run(c)[1]\n"
            "c=base(); c.protocol.recall_mode='cue'; c.sim.snapshot_weights=True; r,h=run(c); out['on']=h\n"
            "s=r.extra['snapshots']; out['labels']=s['labels']; out['t']=[float(x) for x in s['t']]\n"
            "tl=r.timeline; out['expect']=[tl.segment('encode').t0, tl.segment('encode').t1, tl.recalls()[0].t0]\n"
            "out['shape']=list(s['h'].shape); out['n_syn']=int(r.syn_i.size); out['pre_is_baseline']=bool((s['h'][:,0]==1).all() and (s['z'][:,0]==0).all())\n"
            "from neurotape.recall.storage import magnitudes\nm=magnitudes(r,c); out['frac']=m['total']['frac_changed']; out['final_matches']=bool(abs(s['h'][:,-1]-r.h_log[:, -1]).max() < 1.0)")
    h = _subprocess_hashes(code)
    assert h["on"] == h["off"]                                               # instrumentation only: bit-identical spikes
    assert h["labels"] == ["pre_encode", "post_encode", "pre_first_recall"]
    assert np.allclose(h["t"], h["expect"], atol=1e-6) and h["shape"] == [h["n_syn"], 3]
    assert h["pre_is_baseline"] and 0.0 <= h["frac"] <= 1.0
