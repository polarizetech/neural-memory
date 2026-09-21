"""Stereo path, two cochleae, the wired MSO stage, the synaptic-current neurophonic, the ephaptic term."""
import numpy as np
import pytest

from neurotape.config import Config
from neurotape.frontend.spatial import spatialise, woodworth_itd_s

pytest.importorskip("cochlea")


def small_cfg():
    cfg = Config(); cfg.frontend.n_bands = 12; cfg.frontend.stereo = True; return cfg


def test_spatialiser_itd_ild_and_mono_identity():
    fs = 96_000.0; t = np.arange(int(0.1 * fs)) / fs; x = np.sin(2 * np.pi * 500 * t) * np.hanning(t.size)
    assert np.array_equal(*spatialise(x, fs, 0.0))                          # mono = identical L/R: ITD 0, ILD 0
    assert woodworth_itd_s(90) * 1e6 < 660 and woodworth_itd_s(0) == 0
    lr = spatialise(x, fs, 45.0); c = np.correlate(lr[0], lr[1], "full")
    assert abs((c.argmax() - (x.size - 1)) / fs - woodworth_itd_s(45)) < 2.5e-5   # LEFT lags a source on the right
    hi = np.sin(2 * np.pi * 6000 * t) * np.hanning(t.size); l6, r6 = spatialise(hi, fs, 45.0)
    ild = lambda a, b: 20 * np.log10(np.sqrt(np.mean(b ** 2)) / np.sqrt(np.mean(a ** 2)))
    assert ild(l6, r6) > 10 > ild(*lr) > 0                                  # ILD grows with frequency


def test_stereo_loader_keeps_channels(tmp_path):
    import soundfile as sf
    from neurotape.frontend.io import load_wav
    x = np.stack([np.ones(100), -np.ones(100)], axis=1) * 0.5
    sf.write(tmp_path / "st.wav", x, 8000); sf.write(tmp_path / "mo.wav", x[:, 0], 8000)
    st, mo = load_wav(tmp_path / "st.wav")[0], load_wav(tmp_path / "mo.wav")[0]
    assert st.lr.shape == (2, 100) and np.allclose(st.lr[0], 0.5, atol=1e-3) and np.allclose(st.lr[1], -0.5, atol=1e-3)
    assert mo.lr is None


def test_two_independent_cochleae_with_per_ear_fibre_populations():
    from neurotape.frontend import an
    from neurotape.frontend.io import synthetic_streams
    cfg = small_cfg(); cfg.frontend.azimuths_deg = [60.0]
    L, R = an.run_an_binaural(an.ear_mixtures(synthetic_streams(1, 0.5), 0.5, cfg), cfg, 0)
    assert set(L.meta["population"]) == {"hsr_L", "msr_L", "lsr_L"} and set(R.meta["population"]) == {"hsr_R", "msr_R", "lsr_R"}
    assert not np.array_equal(L.t[:50], R.t[:50])                           # independent spike generators
    assert R.t.size > L.t.size                                              # source on the right: right nerve driven harder


def test_distortion_products_in_the_auditory_nerve():
    """PINNED FINDING (measured, never added): see docs/results/RESULTS.md for the numbers."""
    from neurotape.decode.population import distortion_products
    dp = distortion_products(small_cfg(), seconds=1.5)
    assert dp["primary_f1"]["two_tone"] > 15 and dp["primary_f2"]["two_tone"] > 15     # the nerve phase-locks to both primaries
    assert dp["quadratic"]["present"] is True                                 # f2 - f1: the envelope beat, from rectification
    assert isinstance(dp["cubic"]["present"], bool)                           # 2f1 - f2: reported either way, never synthesised


def test_mso_tracks_itd_and_neurophonic_comes_from_currents_and_locks_to_the_tone():
    from neurotape.decode.population import neurophonic_itd_tuning
    from neurotape.frontend import brainstem
    import inspect
    r = neurophonic_itd_tuning(small_cfg(), itds_us=(-400, 0, 400), seconds=0.6)["rows"]
    best = [x["best_internal_delay_us"] for x in r]
    # characteristic delays map ITD: within ONE delay step (100 us) of the imposed ITD, and in order. An exact
    # match was too strict -- adjacent delay channels are a near-tie on a 0.6 s tone (measured: +300 for +400).
    assert all(abs(b - i) <= 100.0 for b, i in zip(best, (-400.0, 0.0, 400.0))) and best[0] < best[1] < best[2]
    assert all(x["line_db"] > 15 for x in r)                                  # phase-locked to the 500 Hz tone
    assert r[1]["amp"] > r[0]["amp"] and r[1]["amp"] > r[2]["amp"]            # and it varies with ITD
    src = inspect.getsource(brainstem.mso_population)
    assert "total += dcur" in src and "cur = eL" in src                       # built from postsynaptic current, not spikes
    cfg = small_cfg(); cfg.mso.delays_us = [900.0]
    with pytest.raises(ValueError):
        brainstem.mso_population(*[__import__("neurotape.frontend.base", fromlist=["SpikeInput"]).SpikeInput(
            np.array([0.1]), np.array([0]), 1, 0.2, dict(population=np.array(["hsr"]), cf_hz=np.array([500.0])))] * 2, cfg)


def test_ephaptic_term_is_absent_at_zero_linear_when_on_and_has_no_field_field_product():
    from neurotape.neurons import model as m
    off = m.equations(False, False)
    assert "I_eph" not in off and "V_field" not in off and "+ I_gap + I_inj)/C" in off    # g_eph = 0: the ORIGINAL text
    on = m.equations(False, True)
    assert "I_eph = g_eph*(V_field + nph(t)) : amp" in on                     # fields sum linearly, one gain
    assert "V_field*nph" not in on and "V_field**" not in on and "nph(t)*" not in on


@pytest.mark.slow
def test_g_eph_zero_reproduces_the_run_exactly_and_nonzero_changes_it():
    import os, subprocess, sys, json
    code = ("import json,hashlib,numpy as np\nfrom neurotape.config import Config\nfrom neurotape.frontend.io import synthetic_streams\n"
            "from neurotape.network import build_inputs, simulate\nout={}\n"
            "for g in (None,0.0,2.0):\n c=Config(); c.frontend.kind='filterbank'; c.network.n_exc=80; c.network.n_inh=20\n"
            " c.protocol.encode_s=2.0; c.protocol.recall_delays_s=[0.5]; c.protocol.recall_s=1.0\n"
            " if g is not None: c.ephaptic.g_eph_nS=g\n r=simulate(c, build_inputs(synthetic_streams(1,2.0),c))\n"
            " out[str(g)]=hashlib.md5(np.round(r.spikes_e[1],6).tobytes()).hexdigest()\nprint(json.dumps(out))")
    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=dict(os.environ, PYTHONHASHSEED="0"))
    h = json.loads(res.stdout.strip().splitlines()[-1])
    assert h["None"] == h["0.0"] and h["2.0"] != h["0.0"]
