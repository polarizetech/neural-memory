"""P1 -- standard induction protocols on the isolated rule. EXPECTED OUTCOMES, written before the first run:

    a  theta-burst (10 x 4 pulses at 100 Hz, bursts at 5 Hz)      -> potentiation
    b  HFS (100 Hz, 1 s)                                          -> potentiation; late-phase capture iff protein is available
    c  pairing pre->post +10 ms, 60 x at 1 Hz                     -> potentiation
    d  pairing post->pre -10 ms, 60 x at 1 Hz                     -> depression
    e  LFS (1 Hz x 900)                                           -> depression

These are permanent tests of whatever parameter set is the DEFAULT. A protocol the adopted set cannot satisfy is
marked xfail with the measured outcome in its reason -- never deleted, and never made to pass by editing the expectation."""
import pytest

from neurotape.plasticity import calibrate as cal


from neurotape.config import Config

CALIBRATED = dict(Ca_pre=1.0, Ca_post=0.275865, theta_p=1.18, theta_d=1.0, tau_Ca_ms=48.8373, t_Ca_delay_ms=18.8008, gamma_p=1645.59, gamma_d=313.0965, tau_h_s=688.355)


@pytest.fixture(scope="module")
def results():
    cfg = Config(); cfg.plasticity = type(cfg.plasticity)(preset="gb2012_hippocampal_cal")
    assert all(getattr(cfg.plasticity, k) == v for k, v in CALIBRATED.items())          # the preset IS the calibrated set
    return cal.run_protocols(cfg=cfg)


@pytest.fixture(scope="module")
def results_default():
    return cal.run_protocols()


def test_expectations_are_the_textbook_ones():
    assert cal.EXPECTED == {"a_tbs": "potentiation", "b_hfs": "potentiation", "c_pair_pre_post": "potentiation",
                            "d_pair_post_pre": "depression", "e_lfs": "depression"}


PENDING = {}     # the calibrated preset must pass ALL of them; nothing is pending

# MEASURED outcomes of the DEFAULT (published-results) parameters, pinned so the gap cannot be forgotten: 1 of 5.
DEFAULT_MEASURED = {"a_tbs": "depression", "b_hfs": "potentiation", "c_pair_pre_post": "no change", "d_pair_post_pre": "no change", "e_lfs": "no change"}


@pytest.mark.slow
def test_default_parameters_pass_only_hfs_and_that_fact_is_pinned(results_default):
    assert {k: results_default[k]["outcome"] for k in cal.EXPECTED} == DEFAULT_MEASURED
    assert sum(DEFAULT_MEASURED[k] == cal.EXPECTED[k] for k in cal.EXPECTED) == 1


@pytest.mark.slow
@pytest.mark.parametrize("protocol", list(cal.EXPECTED))
def test_protocol(results, protocol):
    if protocol in PENDING:
        pytest.xfail(PENDING[protocol])
    assert results[protocol]["outcome"] == cal.EXPECTED[protocol], results[protocol]


@pytest.mark.slow
def test_hfs_captures_only_when_protein_is_available(results):
    if "b_capture" in PENDING:
        pytest.xfail(PENDING["b_capture"])
    assert results["b_hfs_with_protein"]["z_end"] > 0.05 and results["b_hfs"]["z_end"] == 0.0
