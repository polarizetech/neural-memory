"""Minimal habituation model: the instrument checks. Rate periphery and a small network so this runs in
about a minute with no cochlea. Nothing here reads a recognition result."""
import numpy as np
import pytest
from pydantic import ValidationError

from neurotape.experiments.habituation import MEMORY_ARMS, SALIENCE_ARMS, SALIENCE_BASE, _merge
from neurotape.habituation.config import HabConfig
from neurotape.habituation.model import spont_release, eta_pre
from neurotape.habituation.protocol import calibrate_salience, make_sim
from neurotape.habituation.stimuli import family, louder, render, variant

SMALL = dict(periphery=dict(kind="rate", n_cf=16, relay_per_cf=4), network=dict(n_exc=60, n_inh=15))


def small(**over) -> HabConfig:
    return HabConfig.model_validate(_merge(SMALL, over))


def test_unknown_key_raises():
    with pytest.raises(ValidationError):
        HabConfig.model_validate(dict(longterm=dict(mode="hebbian", eta_heb=0.1)))


def test_potentiation_needs_its_substrate():
    with pytest.raises(ValueError):
        HabConfig.model_validate(dict(salience=dict(mode="raw", eta_pot=0.1)))          # longterm off
    with pytest.raises(ValueError):
        HabConfig.model_validate(dict(longterm=dict(mode="hebbian"), salience=dict(mode="off", eta_pot=0.1)))


def test_arms_flip_only_their_switches():
    base = HabConfig().model_dump()
    for name, over in MEMORY_ARMS.items():
        cfg = HabConfig.model_validate(_merge(base, over)).model_dump()
        diff = {(sec, k) for sec in base if isinstance(base[sec], dict) for k in base[sec] if base[sec][k] != cfg[sec][k]}
        assert diff <= {("depression", "on"), ("longterm", "mode")}, (name, diff)


def test_stimulus_relatives_share_what_they_should():
    fam = family(3, 1.0, 5, [1 / 6, 1 / 2])
    x, r = render(fam.stored), render(fam.relatives["reversed"])
    assert np.allclose(x, r[::-1])                                  # reversed = same samples, other order
    X, R = np.abs(np.fft.rfft(x)), np.abs(np.fft.rfft(r))
    assert np.allclose(X, R, rtol=1e-6, atol=1e-6)                   # hence the identical long-term spectrum
    assert variant(fam.stored, "shift", 0.5).env_seeds == fam.stored.env_seeds
    assert louder(fam.stored, 15, 60).level_db == 75


def test_silence_gives_spontaneous_relay_exactly():
    sim, _ = make_sim(small())
    from neurotape.habituation.stimuli import silence
    assert np.all(sim.per.relay_rate(silence(0.5)) == sim.cfg.periphery.relay_spont_hz)


def test_probe_is_paired_and_repeatable():
    sim, st = make_sim(small())
    fam = family(0, 1.0, 5, [])
    rng = np.random.default_rng(1)
    ras = np.stack([sim.raster(s, rng, 0.1) for s in [fam.stored] + fam.novel[:3]])
    a = sim.probe(st, ras, 99).e_count
    b = sim.probe(st, ras, 99).e_count
    assert np.array_equal(a, b)
    assert st.B == 1                                                 # probing copies; the network itself is untouched


def test_eta_pre_holds_L_at_its_spontaneous_target():
    cfg = small(longterm=dict(mode="presynaptic"))
    assert eta_pre(cfg) * spont_release(cfg) * cfg.longterm.tau_s == pytest.approx(1 / cfg.longterm.pre_spont_L - 1)
    sim, st = make_sim(cfg)
    sim.quiet(st, 30.0, np.random.default_rng(0))
    assert abs(st.L.mean() - cfg.longterm.pre_spont_L) < 0.01


@pytest.mark.parametrize("mode", ["presynaptic", "hebbian"])
def test_fast_forward_matches_direct_simulation(mode):
    sim, st = make_sim(small(longterm=dict(mode=mode, eta_hebb=0.2)))
    fam = family(0, 1.0, 5, [])
    rng = np.random.default_rng(2)
    for _ in range(4):
        sim.present(st, fam.stored, rng); sim.quiet(st, 1.0, rng)
    a, b = st.copy(), st.copy()
    sim.fast_forward(a, 60.0)
    sim.quiet(b, 60.0, np.random.default_rng(3))
    assert np.abs(a.xs.mean() - b.xs.mean()) < 0.01
    assert np.abs(a.xf.mean() - b.xf.mean()) < 0.03
    dL_a, dL_b = (a.L - st.L).mean(), (b.L - st.L).mean()           # the change over the minute, not the level
    assert abs(dL_a - dL_b) <= 0.15 * max(abs(dL_b), 1e-4)


def test_no_depression_no_longterm_means_no_state_to_carry():
    sim, st = make_sim(small(depression=dict(on=False), longterm=dict(mode="off")))
    fam = family(0, 1.0, 5, [])
    x = st.copy()
    for _ in range(3):
        sim.present(x, fam.stored, np.random.default_rng(4))
    assert np.all(x.xf == st.xf) and np.all(x.xs == st.xs) and x.L is None


@pytest.mark.parametrize("mode", ["raw", "network"])
def test_salience_gain_is_solved_to_its_target(mode):
    cfg = small(**_merge(SALIENCE_BASE, SALIENCE_ARMS[mode]))
    sim, st = make_sim(cfg)
    fam = family(0, 1.0, 5, [], n_interf=11)
    calibrate_salience(sim, st, fam.interference[8:])
    from dataclasses import replace
    from neurotape.habituation.model import run
    cc = cfg.model_copy(deep=True); cc.salience.gain, cc.salience.eta_pot = 0.0, 0.0
    net_c = replace(sim.net, cfg=cc); sim_c = replace(sim, cfg=cc, net=net_c)
    peaks = []
    for j, spec in enumerate(fam.interference[8:]):
        s = st.copy()
        loud = louder(spec, cfg.protocol.salient_db, cfg.periphery.level_db_spl)
        rec = run(net_c, s, sim_c.raster(loud, np.random.default_rng(cfg.seed + 700 + j)), np.random.default_rng(cfg.seed + 800 + j))
        peaks.append(rec.nm.max())
    assert np.mean(peaks) == pytest.approx(cfg.salience.nm_target, rel=1e-6)


def test_slow_per_spike_shares_the_spontaneous_steady_state():
    """The exploratory per-spike slow pool is derived to sit where the per-release one sits in silence;
    only DRIVEN channels may differ. Checked by direct simulation, and the fast-forward agrees."""
    out = {}
    for per in ("release", "spike"):
        sim, st = make_sim(small(depression=dict(slow_per=per)))
        sim.quiet(st, 60.0, np.random.default_rng(0))
        ff = st.copy(); sim.fast_forward(ff, 60.0)
        out[per] = (st.xs.mean(), ff.xs.mean())
    assert abs(out["release"][0] - out["spike"][0]) < 0.02
    assert abs(out["spike"][0] - out["spike"][1]) < 0.02


def test_frozen_recovery_leaves_uneroded_synapses_alone():
    """tau = inf with post_spont = 0 somewhere: the fast-forward must leave L finite and unchanged there."""
    import math
    sim, st = make_sim(small(longterm=dict(mode="hebbian", eta_hebb=0.2)))
    sim.post_spont[:5] = 0.0
    cc = sim.cfg.model_copy(deep=True); cc.longterm.tau_s = math.inf
    from dataclasses import replace
    fz = replace(sim, cfg=cc, net=replace(sim.net, cfg=cc))
    before = st.L.copy()
    fz.fast_forward(st, 600.0)
    assert np.all(np.isfinite(st.L))
    assert np.array_equal(st.L[:, :, :5], before[:, :, :5])
