"""Calcium-based early-phase plasticity + synaptic tagging and capture.

Equations are those of Luboeinski & Tetzlaff 2021, Commun Biol 4:275
(https://doi.org/10.1038/s42003-021-01778-y), read from the authors' Brian2 implementation
jlubo/brian_network_plasticity (``brianNetworkConsolidation.py``, ``get_model``), which carries
no licence file -- so the *equations and published parameter values* are reused here and the code
is written fresh. The calcium thresholds are Graupner & Brunel 2012, PNAS 109:3991, as adopted
there. The neuromodulator-dependent protein-synthesis threshold is Lehr, Luboeinski & Tetzlaff
2022, Sci Rep 12:17772 (jlubo/memory-consolidation-stc, Apache-2.0).

Reference form (h in volts, h_0 = 4.20075 mV):

    dh/dt  = ( 0.1 (h_0 - h) + gamma_p (10 mV - h) H(Ca - theta_p) - gamma_d h H(Ca - theta_d)
               + sqrt(tau_h (H(Ca-theta_p) + H(Ca-theta_d))) sigma_pl xi ) / tau_h
    dCa/dt = -Ca / tau_Ca          (+ Ca_pre on a delayed pre spike, + Ca_post on a post spike)
    dz/dt  = ( alpha p (1 - z) H((h - h_0) - theta_tag) - alpha p (z + 0.5) H((h_0 - h) - theta_tag) ) / tau_z
    dp/dt  = ( -p + alpha H(sum_i |h_i - h_0| - theta_pro) ) / tau_p       [per postsynaptic neuron]
    w      = h + z h_0

Here h is dimensionless (h / h_0), so every threshold keeps its published ratio to h_0.

DEVIATIONS, each also in ASSUMPTIONS.md:
  1. Time compression F (default 60x) is applied ONLY to the hours-scale terms: the 0.1(h_0-h)
     decay of the early phase, tau_p and tau_z. Induction (the gamma terms and their noise) runs
     at the published rate. The reference instead fast-forwards analytically through silent periods.
  2. T-current calcium: the calcium seen by a synapse is Ca + c_T * CaT_post. Placeholder.
  3. Plasticity ODEs integrate on their own 1 ms clock; spikes are still handled at the neuron dt.
  4. The synapse is conductance-based: the delivered weight is g0 * (h + z) siemens.
"""
from __future__ import annotations

from brian2 import ms, second

from ..config import Config

PLASTIC_MODEL = """
dh/dt = decay_rate*(1 - h)
        + plastic_on*(gamma_p*(h_max - h)*LTP - gamma_d*h*LTD)/tau_h
        + plastic_on*noise_on*sqrt((LTP + LTD)/tau_h)*sigma_pl*xi_pl : 1 (clock-driven)
dCa/dt = -Ca/tau_Ca : 1 (clock-driven)
Ca_tot = Ca + c_T*CaT_post : 1
LTP = int(Ca_tot > theta_p) : 1
LTD = int(Ca_tot > theta_d) : 1
tag_p = tag_on*int((h - 1) > theta_tag) : 1
tag_d = tag_on*int((1 - h) > theta_tag) : 1
dz/dt = (alpha_c*p_post*(1 - z)*tag_p - alpha_c*p_post*(z + 0.5)*tag_d)/tau_z : 1 (clock-driven)
sum_h_diff_post = abs(h - 1) : 1 (summed)
"""

ON_PRE = {"pre_v": "g_e_post += g0*clip(h + z, 0, 10)", "pre_ca": "Ca += Ca_pre*plastic_on"}
ON_POST = "Ca += Ca_post*plastic_on"


def plastic_model(cfg: Config) -> str:
    """The synapse equations, with the early-phase WRITE multiplied by a gate when any gating mechanism is on.
    With none on this returns PLASTIC_MODEL unchanged (hash-pinned). Every gate factor reads network-internal
    variables of the postsynaptic cell, except C6's, which is an evaluation mode and is labelled non-biological."""
    m, g = cfg.mechanisms, cfg.mismatch_gate
    factors = []
    if m.mismatch_gate:
        mid = "lab_gain*lab_post" if m.lability_window else "1"     # mid regime: only the reactivated assembly is labile
        factors.append(f"(int(M_pop_post >= th_low)*(int(M_pop_post <= th_high)*{mid} + int(M_pop_post > th_high)"
                       f"*clip(creb_post/creb_ref, 0, 1)*int(z < z_protect)))")
    elif m.lability_window:
        factors.append("(1 + (lab_gain - 1)*lab_post)")             # C3 alone: a gain on top of ordinary plasticity
    freeze = cfg.eval.freeze_plasticity_at_recall
    if freeze:
        factors.append("pl_t(t)")                                    # C6: NON-BIOLOGICAL evaluation schedule
    if not factors:
        return PLASTIC_MODEL
    text = PLASTIC_MODEL.replace("plastic_on*(gamma_p", "plastic_on*pgate*(gamma_p").replace("plastic_on*noise_on*sqrt(", "plastic_on*pgate*noise_on*sqrt(")
    assert text.count("pgate") == 2
    if freeze:
        text = text.replace("dz/dt = (", "dz/dt = pl_t(t)*(")
        assert text.count("pl_t(t)") == 1
    return text + "pgate = " + "*".join(factors) + " : 1\n"


def namespace(cfg: Config) -> dict:
    pl, m, F = cfg.plasticity, cfg.mechanisms, cfg.time_compression
    from brian2 import nS
    return dict(
        decay_rate=0.1 / (pl.tau_h_s / F * second),      # compressed
        tau_h=pl.tau_h_s * second,                       # induction: NOT compressed
        gamma_p=pl.gamma_p, gamma_d=pl.gamma_d, h_max=pl.h_max, sigma_pl=pl.sigma_pl,
        tau_Ca=pl.tau_Ca_ms * ms, theta_p=pl.theta_p, theta_d=pl.theta_d,
        Ca_pre=pl.Ca_pre, Ca_post=pl.Ca_post, theta_tag=pl.theta_tag,
        alpha_c=pl.alpha, tau_z=pl.tau_z_s / F * second,  # compressed
        c_T=pl.c_T if m.t_current else 0.0,
        tag_on=1.0 if m.tagging else 0.0,
        plastic_on=1.0 if m.plasticity else 0.0,
        noise_on=1.0 if pl.noise else 0.0,
        g0=cfg.network.g0_nS * nS,
        lab_gain=cfg.lability.gain,
        th_low=cfg.mismatch_gate.theta_low, th_high=cfg.mismatch_gate.theta_high,
        z_protect=cfg.mismatch_gate.z_protect, creb_ref=cfg.mismatch_gate.creb_ref,
    )


def delays(cfg: Config) -> dict:
    return {"pre_v": cfg.network.axon_delay_ms * ms, "pre_ca": cfg.plasticity.t_Ca_delay_ms * ms}
