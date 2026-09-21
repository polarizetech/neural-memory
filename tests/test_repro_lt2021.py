"""R2 metric code and builder for the Luboeinski & Tetzlaff 2021 reproduction (docs/repro/TARGET.md)."""
import numpy as np

from neurotape.experiments import repro_lt2021 as R


def test_window_is_half_a_second_centred_on_the_readout():
    t = np.array([19.84, 19.85, 20.0, 20.349, 20.35]); i = np.zeros(5, int)
    assert R.window_rates(i, t, 20.1, 2)[0] == 3 / 0.5          # [19.85, 20.35): the first and last spike fall outside


def test_q_star_is_the_papers_eq17():
    v = np.zeros(1600); v[:75] = 94.0; v[75:150] = 10.0; v[150:] = 8.0
    q = R.q_star(v, np.arange(75), np.arange(75, 150), np.arange(150, 1600))
    assert abs(q["Q"] - (10.0 - 8.0) / 94.0) < 1e-12


def test_mutual_information_limits():
    rng = np.random.default_rng(0); a = rng.integers(0, 4, 4000).astype(float); b = rng.integers(0, 4, 4000).astype(float)
    assert abs(R.mutual_information(a, a) - R._entropy(a[:, None])) < 1e-12      # identical patterns: MI = H
    assert R.mutual_information(a, b) < 0.01                                      # independent patterns: MI ~ 0


def test_reference_readout_is_a_relabelling_so_mi_is_unchanged_and_q_moves():
    rng = np.random.default_rng(1); a = rng.poisson(2.0, 1600) / 0.5; b = rng.poisson(3.0, 1600) / 0.5
    assert abs(R.mutual_information(R.reference_readout(a), R.reference_readout(b)) - R.mutual_information(a, b)) < 1e-12
    v = np.zeros(1600); v[:75] = 94.0; v[75:150] = rng.poisson(5, 75) / 0.5; v[150:] = rng.poisson(4, 1450) / 0.5
    args = (np.arange(75), np.arange(75, 150), np.arange(150, 1600))
    assert R.q_star(R.reference_readout(v), *args)["Q"] != R.q_star(v, *args)["Q"]
    assert np.all(R.reference_readout(v)[v == 0] == 0) and np.all(R.reference_readout(v)[v > 0] == v[v > 0] + 2.0)


def test_tag_counts_split_by_sign_and_by_assembly():
    si = np.array([0, 1, 200, 300]); sj = np.array([1, 0, 0, 301]); h = np.array([1.5, 0.7, 1.1, 1.0]); z = np.array([0.2, -0.1, 0.0, 0.0])
    c = R.tag_counts(h, z, 150, 0.2, si, sj)
    wa = c["within_assembly"]
    assert (wa["n"], wa["tag_pot"], wa["tag_dep"], wa["late_pot"], wa["late_dep"]) == (2, 1, 1, 1, 1) and abs(wa["mean_w"] - 1.15) < 1e-12
    assert c["all"]["tag_pot"] == 1 and c["all"]["tag_dep"] == 1 and c["outside_assembly"]["n"] == 2


def test_score_applies_the_preregistered_criteria():
    mk = lambda q, mi, ans, ca: dict(ok=True, Q=q, Q_ref_readout=q, MI=mi, nu_ans=ans, nu_control_assembly=ca)
    s = R.score([mk(0.030, 0.87, 10, 7)] * 10, [mk(0.035, 0.97, 12, 9)] * 10)
    assert s["a_pass"] and s["b_pass"] and s["c_pass"] and abs(s["gain_Q"] - (0.035 / 0.030 - 1)) < 1e-9
    s = R.score([mk(0.001, 0.2, 1.0, 1.1)] * 10, [mk(0.0005, 0.1, 1.0, 1.1)] * 10)
    assert not s["a_pass"] and not s["b_pass"] and not s["c_pass"]


def test_every_variant_changes_the_config_and_only_as_is_changes_nothing():
    from neurotape.config import Config
    base = R.base_config(0, {}).model_dump()
    ref = Config(); ref.network.n_exc, ref.network.n_inh = R.N_EXC, R.N_INH; ref.mechanisms.nm_dynamic = False
    assert base == ref.model_dump()                               # as-is = neurotape's defaults at the paper's size
    for name, v in R.VARIANTS.items():
        if name in ("as_is", "lif", "theta_pro", "fast_forward"):  # the last two act in the builder, not the config
            continue
        assert R.base_config(0, v).model_dump() != base, name


def test_small_network_smoke(tmp_path):
    """One real build at 1/8 size: stimulated cells fire at the refractory limit, as the paper's do; the assembly's
    synapses are tagged; nothing outside the stimulated cells is driven by the stimulus."""
    r = R.simulate(seed=3, recall="8h", consolidate_sim_s=2.0, n_exc=200, n_inh=50)
    assert 400 <= r["rate_learning_pulse_hz"] <= 500 and 400 <= r["rate_cue_pulse_hz"] <= 500
    assert abs(r["nu_as"] - r["rate_cue_pulse_hz"] * 0.1 / 0.5) < 6
    wa = r["tags"]["end_of_learning"]["within_assembly"]
    assert wa["tag_pot"] > 0.9 * wa["n"] and r["tags"]["pre_learning"]["all"]["tag_pot"] == 0
    assert len(r["counts_recall"]) == 200 and set(r["tags"]) == {"pre_learning", "end_of_learning", "pre_10s_recall", "pre_8h_recall"}
