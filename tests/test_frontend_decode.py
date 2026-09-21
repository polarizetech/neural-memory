"""Front ends, NM, theta, plasticity arithmetic, readout, config, playback labelling."""
import numpy as np
import pytest

from neurotape.config import Config
from neurotape.frontend.io import synthetic_streams, load_csv
from neurotape.frontend.filterbank import analyse
from neurotape.frontend.mixing import projection, stream_purity
from neurotape.frontend.base import StageUnavailable
from neurotape.decode import readout as ro
from neurotape.decode import population as pop


def test_config_rejects_unknown_key_and_ablations_flip_one_switch():
    with pytest.raises(Exception):
        Config.model_validate({"mechanisms": {"t_curent": False}})       # a typo must not run the full model
    from neurotape.experiments.suite import ABLATIONS, ablated
    base = Config()
    for name in ABLATIONS:
        diff = [k for k, v in ablated(base, name).mechanisms.model_dump().items() if v != getattr(base.mechanisms, k)]
        assert len(diff) == 1, (name, diff)


def test_filterbank_envelopes_and_sensor_band():
    s = synthetic_streams(1, 2.0)[0]
    a = analyse(s, Config().frontend)
    assert a.env.shape == (32, 2000) and a.env.min() >= 0 and np.isfinite(a.env).all()
    cfg = Config(); cfg.frontend.filterbank = "logbp"; cfg.frontend.f_lo_hz = 0.1; cfg.frontend.f_hi_hz = 10.0; cfg.frontend.n_bands = 6
    from neurotape.frontend.io import Stream
    t = np.arange(0, 120, 1 / 50.0)
    a = analyse(Stream("sensor", np.sin(2 * np.pi * 0.3 * t), 50.0, "synthetic:sensor"), cfg.frontend)
    assert a.fcs[0] == pytest.approx(0.1) and a.env.shape[1] == 120_000
    with pytest.raises(Exception):
        Config.model_validate({"frontend": {"filterbank": "gammatone", "f_lo_hz": 0.1}})


def test_csv_without_rate_is_refused(tmp_path):
    p = tmp_path / "c.csv"; p.write_text("x\n1\n2\n3\n")
    with pytest.raises(ValueError):
        load_csv(p, None)
    p.write_text("t,x,y\n0,1,2\n0.1,2,3\n0.2,3,4\n")
    st = load_csv(p, None)
    assert len(st) == 2 and st[0].fs == pytest.approx(10.0)


def test_mixed_projection_draws_from_all_streams_labelled_does_not():
    rng = np.random.default_rng(0); cfg = Config().mixing
    P = projection(3, 32, cfg, rng)
    assert np.allclose(P.sum(1), 1) and (P >= 0).all()
    assert (P.reshape(cfg.n_input, 3, 32).sum(2) > 0).sum(1).mean() > 2.0
    cfg2 = cfg.model_copy(); cfg2.mode = "labelled"
    assert stream_purity(projection(3, 32, cfg2, rng), 3).mean() > stream_purity(P, 3).mean() + 0.2


def test_an_front_end_keeps_fibre_types_on_a_tonic_phasic_axis():
    pytest.importorskip("cochlea")
    from neurotape.frontend import an
    cfg = Config(); cfg.frontend.n_bands = 6
    s = synthetic_streams(2, 1.0)
    si = an.run_an(an.acoustic_mixture(s, 1.0, 60.0), cfg, seed=0)
    ax = an.fibre_axis(si)
    assert set(ax) == {"hsr", "msr", "lsr"}
    assert ax["hsr"]["rate_hz"] > ax["msr"]["rate_hz"] > ax["lsr"]["rate_hz"]            # tonic end
    assert ax["lsr"]["modulation_depth"] > ax["hsr"]["modulation_depth"]                # phasic end
    assert si.meta["cf_hz"].min() >= 125.0 and any("125" in n for n in si.notes)
    cfg.frontend.moc_enabled = True
    quiet = an.run_an(an.acoustic_mixture(s, 1.0, 60.0), cfg, seed=0, nm_tonic=0.4)
    assert quiet.mean_rate() < si.mean_rate()                                           # efferent gain turns the cochlea down


def test_optional_stages_raise_instead_of_falling_back():
    from neurotape.frontend.retina import encode_video
    from neurotape.frontend.brainstem import cn_stage, mso_stage
    from neurotape.frontend.base import SpikeInput
    with pytest.raises(StageUnavailable):
        encode_video("x.mp4")
    si = SpikeInput(np.array([0.1]), np.array([0]), 1, 1.0, dict(population=np.array(["hsr"]), cf_hz=np.array([500.0])))
    with pytest.raises(StageUnavailable):
        cn_stage(si)
    with pytest.raises(ValueError):
        mso_stage(si, si, delays_us=(900,))                                             # 660 us ITD ceiling
    rng = np.random.default_rng(0); t = np.sort(rng.uniform(0, 1, 400))
    L = SpikeInput(t, np.zeros(400, int), 1, 1.0, dict(population=np.array(["hsr"]), cf_hz=np.array([500.0])))
    R = SpikeInput(t + 300e-6, np.zeros(400, int), 1, 1.0, L.meta)
    out = mso_stage(L, R)
    counts = np.bincount(out.i, minlength=out.n)
    assert out.meta["best_delay_us"][counts.argmax()] == -300                           # tuned to the imposed ITD


def test_nm_flat_ablation_and_phasic_events():
    from neurotape.neuromod.nm import build_nm
    from neurotape.recall.protocol import build_timeline
    cfg = Config(); cfg.protocol.encode_s = 10.0
    env = np.full((1, 4, 10_000), 0.2); env[:, :, 5000:5200] = 1.0                      # one surprise
    tr = build_nm(cfg, build_timeline(cfg), env, 1000.0)
    assert len(tr.events_s) >= 1 and tr.nm.max() > cfg.neuromod.tonic + 0.05
    cfg.mechanisms.nm_dynamic = False
    flat = build_nm(cfg, build_timeline(cfg), env, 1000.0)
    assert np.ptp(flat.nm) == 0 and flat.nm[0] == cfg.neuromod.tonic
    cfg.mechanisms.nm_dynamic = True; cfg.attention.stream = 0
    att = build_nm(cfg, build_timeline(cfg), env, 1000.0)
    assert att.nm[(att.t > 6.05) & (att.t < 6.15)].mean() > tr.nm[(tr.t > 6.05) & (tr.t < 6.15)].mean()


def test_theta_reset_aligns_phase_to_onsets():
    from neurotape.neuromod.theta import build_theta, envelope_onsets
    cfg = Config(); on = np.array([1.0, 2.37, 3.11])
    cfg.theta.mode = "reset"; t, th, ph = build_theta(cfg, 5.0, on, 0)
    assert all(abs(th[int(o * 1000)] - 1.0) < 1e-6 for o in on)
    cfg.theta.mode = "free"; _, th2, _ = build_theta(cfg, 5.0, on, 0)
    assert not all(abs(th2[int(o * 1000)] - 1.0) < 1e-3 for o in on)
    cfg.mechanisms.theta = False; assert not build_theta(cfg, 5.0, on, 0)[1].any()
    e = np.zeros(3000); e[1000:1300] = 1; e[2000:2300] = 1
    assert np.allclose(envelope_onsets(e, 1000.0, 1.5, 0.15), [1.0, 2.0], atol=0.03)


def test_time_compression_touches_only_the_slow_terms():
    from neurotape.plasticity import stc
    from brian2 import second
    a, b = Config(), Config(); b.time_compression = 1.0
    na, nb = stc.namespace(a), stc.namespace(b)
    assert na["tau_h"] == nb["tau_h"] and na["gamma_p"] == nb["gamma_p"]               # induction untouched
    assert float(na["decay_rate"] / nb["decay_rate"]) == pytest.approx(60.0)
    assert float(nb["tau_z"] / na["tau_z"]) == pytest.approx(60.0)
    assert "60x" in a.compression_label()
    a.mechanisms.tagging = False; assert stc.namespace(a)["tag_on"] == 0.0


def test_readout_recovers_a_linear_code_and_the_null_rejects_silence():
    rng = np.random.default_rng(0)
    Y = np.abs(rng.standard_normal((800, 6))).cumsum(0) % 3.0
    X = Y @ rng.standard_normal((6, 40)) + 0.05 * rng.standard_normal((800, 40))
    d = ro.fit_ridge(X[:600], Y[:600], [1e-2, 1.0, 100.0])
    assert ro.mean_corr(d.predict(X[600:]), Y[600:]) > 0.95
    C = ro.crosstalk(d.predict(X[600:]), Y[600:], 2)
    assert C[0, 0] > 0.9 and C[1, 1] > 0.9
    blip = np.zeros((300, 3)); blip[rng.integers(0, 300, 4)] = 1.0                      # a near-silent network
    env = np.abs(np.sin(np.linspace(0, 20, 300)))[:, None] * np.ones((1, 3)) + 0.05 * rng.standard_normal((300, 3))
    res = [ro.bestlag_with_null(np.roll(blip, s, 0), env, 100.0, 0.5, 60, s)["p"] for s in range(12)]
    assert np.mean(np.array(res) < 0.05) <= 0.25                                        # the shift null does not pass blips


def test_ordering_score_detects_order():
    rng = np.random.default_rng(1)
    true = rng.standard_normal((1200, 4)).cumsum(0)
    assert ro.ordering_score(true[:600], true, 100.0) > 0.9
    assert abs(ro.ordering_score(rng.standard_normal((600, 4)), true, 100.0)) < 0.6


def test_phase_lag_separates_fixed_latency_from_fixed_phase():
    fs, rates = 1000.0, pop.DOELLING_2019["rates_nps"]
    t = np.arange(0, 30, 1 / fs); ev, osc = [], []
    for f in rates:
        s = np.sin(2 * np.pi * f * t)
        ev.append(pop.phase_lag(s, np.sin(2 * np.pi * f * (t - 0.100)), fs, f)[0])      # 100 ms latency
        osc.append(pop.phase_lag(s, np.sin(2 * np.pi * f * t - 0.8), fs, f)[0])        # constant phase
    assert pop.effective_latency_ms(rates, ev) == pytest.approx(100.0, abs(8.0))
    assert pop.pcm(osc) > 0.95 > pop.pcm(ev)
    assert "oscillator" in pop.pcm_verdict(pop.pcm(osc))


def test_playback_files_must_be_labelled_reconstructions(tmp_path):
    from neurotape.decode.vocoder import vocode, write_reconstruction
    a = analyse(synthetic_streams(1, 1.0)[0], Config().frontend)
    x = vocode(ro.resample_targets(a.env[None], 1000.0, 100.0), a.fcs, a.env_scale, Config().frontend, 100.0)
    assert np.isfinite(x).all() and np.abs(x).max() <= 0.9 + 1e-9
    with pytest.raises(AssertionError):
        write_reconstruction(tmp_path / "output.wav", x)
    write_reconstruction(tmp_path / "reconstruction_x.wav", x)
    from neurotape.decode.connear import load_connear
    with pytest.raises(StageUnavailable):
        load_connear(tmp_path)


def test_ci95_and_beats_rule():
    from neurotape.experiments.common import ci95, paired_diff
    c = ci95([1.0, 1.1, 0.9, 1.0]); assert c["lo"] < 1.0 < c["hi"] and c["n"] == 4
    assert paired_diff([1, 1.1, 0.9, 1.2], [0, 0.1, 0.0, 0.1])["beats"]
    assert not paired_diff([1, -1, 0.5, -0.5], [0, 0, 0, 0])["beats"]
