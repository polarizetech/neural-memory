"""One small network, built and run once (slow). Pins the structural facts the experiments rely on."""
import numpy as np
import pytest

from neurotape.config import Config


@pytest.fixture(scope="module")
def run():
    from neurotape.frontend.io import synthetic_streams
    from neurotape.network import build_inputs, simulate
    from neurotape.recall.evaluate import evaluate
    cfg = Config(); cfg.frontend.kind = "filterbank"; cfg.protocol.encode_s = 4.0; cfg.protocol.recall_delays_s = [1.0]
    cfg.decode.n_surrogates = 20; cfg.network.n_exc = 120; cfg.network.n_inh = 30
    inp = build_inputs(synthetic_streams(2, 4.0), cfg); res = simulate(cfg, inp)
    ev, dec = evaluate(res, inp, cfg)
    return cfg, inp, res, ev


@pytest.mark.slow
def test_timeline_states_ranks_and_lfp(run):
    cfg, inp, res, ev = run
    assert [s.kind for s in res.timeline.segments] == ["settle", "encode", "consolidate", "recall"]
    assert set(np.unique(res.state_e)) <= {0, 1, 2, 3}
    assert res.state_t.min() >= res.timeline.segment("encode").t0 - 1e-6       # logged only where asked
    from neurotape.decode.readout import rank_table
    t_end, rank, fired = rank_table(res, res.timeline.segment("encode"))
    assert rank.shape == fired.shape and rank.shape[1] == 80                  # 4 s / 50 ms
    assert all(sorted(rank[:, k]) == list(range(120)) for k in (0, 40, 79))   # a full ranking every window
    assert fired[rank < 12].mean() > fired[rank >= 60].mean()                 # high drive rank -> fires more
    assert res.lfp_Ie.size == res.lfp_Ii.size and np.abs(res.lfp_Ie).max() > 0


@pytest.mark.slow
def test_decoder_is_trained_on_encode_only_and_reads_the_code(run):
    cfg, inp, res, ev = run
    assert ev["encode_heldout_r"][0] > 0.3
    assert len(ev["recall"]) == 1 and "bestlag" in ev["recall"][0] and "locked_r__non_engram" in ev["recall"][0]
    assert np.isfinite(ev["trf"]["r_heldout"])


@pytest.mark.slow
def test_input_weight_is_normalised_across_front_ends(run):
    cfg, inp, res, ev = run
    k_in = cfg.mixing.p_in_exc * inp.spikes_enc.n
    g_mean = res.extra["w_in_nS"] * k_in * inp.spikes_enc.mean_rate() * cfg.network.tau_e_ms * 1e-3
    assert g_mean == pytest.approx(cfg.mixing.g_in_mean_nS, rel=1e-6)
