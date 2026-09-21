"""Single-compartment conductance-based neuron: leak + AdEx spike mechanism + T-type Ca + adaptation.

Sources
-------
* Spike mechanism and adaptation: adaptive exponential integrate-and-fire,
  Brette & Gerstner 2005, J Neurophysiol 94:3637.
* Low-threshold T-type calcium current with voltage-dependent inactivation: the reduced
  (instantaneous-activation) thalamocortical I_T of Destexhe, Bal, McCormick & Sejnowski 1996,
  J Neurophysiol 76:2049, fitted to Huguenard & McCormick 1992, J Neurophysiol 68:1373.
  Kinetics checked this build against ModelDB 3343 ``IT.mod``:
      m_inf = 1/(1+exp(-(Vm+57)/6.2)),  h_inf = 1/(1+exp((Vm+81)/4)),
      tau_h = (30.8 + (211.4 + exp((Vm+113.2)/5)) / (1 + exp((Vm+84)/3.2))) / phi_h,
      Vm = V + shift (2 mV), phi_h = 3^((T-24)/10),  I_T = g_T m_inf^2 h (V - E_Ca).
  g_T is NOT from that model (theirs is a density on a 29,000 um^2 cell); it is set so the
  single-cell unit tests pass -- see ASSUMPTIONS.md.
* Background current: Ornstein-Uhlenbeck, as in Luboeinski & Tetzlaff 2021 (tau_OU = 5 ms).
* Protein pool p: Luboeinski & Tetzlaff 2021 eq. for p, with the neuromodulator-dependent
  threshold theta_pro = h_0/(NM + 0.001) of Lehr, Luboeinski & Tetzlaff 2022
  (jlubo/memory-consolidation-stc, Network.cpp, protein-synthesis-threshold function).

State enum (logged per neuron per logging step): 0 REST, 1 LOADED, 2 SPIKE, 3 RESET.
BURST is a property of a spike *sequence*, so it is annotated post hoc from spike times
(``annotate_bursts``) rather than being an instantaneous state.
"""
from __future__ import annotations

import numpy as np
import brian2 as b2
from brian2 import ms, mV, nS, pA, pF, nA, second, amp

from ..config import Config, NeuronParams

REST, LOADED, SPIKE, RESET = 0, 1, 2, 3
STATE_NAMES = {REST: "REST", LOADED: "LOADED", SPIKE: "SPIKE/BURST", RESET: "RESET"}

EQUATIONS = """
dV/dt = (gL*(EL - V) + gL*DeltaT*exp(clip((V - VT_eff)/DeltaT, -50, 8)) - __AHP__w - I_T
         + I_syn + I_bg + I_drift + I_nm + I_theta + I_gap + I_inj__EPH__)/C : volt (unless refractory)
dw/dt = (a*(V - EL) - w)/tau_w : amp
VT_eff = VT - dVT_creb*clip(creb, 0, 1)__VTNM__ : volt

# --- T-type calcium current (Destexhe et al. 1996; ModelDB 3343) ---
Vm = clip(V, -120*mV, -20*mV) + T_shift : volt
m_inf = 1/(1 + exp(-(Vm + 57*mV)/(6.2*mV))) : 1
hT_inf = 1/(1 + exp((Vm + 81*mV)/(4*mV))) : 1
tau_hT = (30.8*ms + (211.4*ms + exp((Vm + 113.2*mV)/(5*mV))*ms)/(1 + exp((Vm + 84*mV)/(3.2*mV))))/phi_h : second
dhT/dt = (hT_inf - hT)/tau_hT : 1
I_T = gT*m_inf**2*hT*(V - E_Ca) : amp
gT : siemens (constant)

# --- synaptic conductances ---
I_syn = (g_ext + g_e)*(E_e - V) + g_i*(E_i - V) + g_b*(E_K - V) : amp
dg_ext/dt = -g_ext/tau_e : siemens
dg_e/dt = -g_e/tau_e : siemens
dg_i/dt = -g_i/tau_i : siemens
dg_b/dt = -g_b/tau_b : siemens      # slow GABA_B-like K+ conductance (see ASSUMPTIONS.md)

# --- background noise (fast OU) and tonic operating point (slow OU drift) ---
dI_bg/dt = (I0 - I_bg)/tau_bg + sigma_bg*noise_scale(t)*sqrt(2/tau_bg)*xi_bg : amp
dI_drift/dt = -I_drift/tau_drift + sigma_drift*sqrt(2/tau_drift)*xi_drift : amp
I_nm = k_inh*(NM(t) - nm_ref) : amp
I_theta = theta_amp*theta(t) : amp
I_exc = (g_ext + g_e)*(E_e - V) : amp
I_rec = g_e*(E_e - V) : amp
I_inh = g_i*(E_i - V) + g_b*(E_K - V) : amp
I_gap : amp
I_inj : amp

# --- calcium, CREB-like excitability variable, protein pool ---
dCaT/dt = -CaT/tau_CaT + k_CaT*clip(-I_T, 0*amp, 10*nA) : 1
dCa_s/dt = -Ca_s/tau_Cas + k_T_s*clip(-I_T, 0*amp, 10*nA) : 1
dcreb/dt = creb_on*(Ca_s - creb)/tau_creb : 1
dp/dt = (-p + alpha_p*int(sum_h_diff > theta_pro))/tau_p : 1
theta_pro = nm_dep*theta_pro_scale/(NM(t) + 0.001) + (1 - nm_dep)*theta_pro_const : 1
sum_h_diff : 1

# --- rank bookkeeping: mean excitatory CONDUCTANCE over the current rank window. Conductance, not
# current: the current carries a (E_e - V) factor, so an inhibited, silent cell out-ranked a firing
# one by 40% on driving force alone (measured: top-decile cells fired in 0.4% of windows).
ddrive_acc/dt = (g_ext + g_e)/rank_window : siemens

# --- explicit state enum ---
since_spike = t - lastspike : second
nstate = 2*int(since_spike < t_spike_w)
      + 3*int(since_spike >= t_spike_w and since_spike < t_reset_w)
      + 1*int(since_spike >= t_reset_w and hT > hT_loaded) : integer
"""

NM_EXC_EQS = """
# --- NM -> excitability (Bacon, Pickering & Mellor 2020): AHP block + threshold drop, E cells only ---
nm_x = clip(NM(t) - nm_ref, 0, 1) : 1
ahp_scale = clip(1 - k_ahp*nm_x, 0, 1) : 1
"""


EPH_EQS = """
# --- ephaptic term: a small current from the local field. Fields SUM LINEARLY (network LFP + MSO
# neurophonic); there is no field-field product anywhere. The nonlinearity is the membrane's own.
V_field : volt
I_eph = g_eph*(V_field + nph(t)) : amp
"""


TRACE_EQS = """
# --- C1 intrinsic excitability trace = the CREB-like variable, now also reducing adaptation ---
tr_ahp = 1 - k_tr_ahp*clip(creb, 0, 1) : 1
"""


REPULSION_EQS = """
# --- C4 option: recent use raises threshold ("seek novel"). SIGN UNSETTLED in the literature. ---
du_use/dt = -u_use/tau_use : 1
"""


CURRENT_TRACE_EQS = """
# --- the cell's OWN feedforward and recurrent excitatory currents, low-passed (C2 / C3 / C5 read these) ---
I_ff = g_ext*(E_e - V) : amp
dff_lp/dt = (I_ff - ff_lp)/tau_mm : amp
drec_lp/dt = (I_rec - rec_lp)/tau_mm : amp
mism = abs(ff_lp - rec_lp)/(abs(ff_lp) + abs(rec_lp) + mm_eps) : 1
"""
LABILITY_EQS = """
# --- C3: lability opened by a recurrently-dominated spike, closing on its own ---
dlab/dt = -lab/tau_lab : 1
"""
MISMATCH_EQS = """
M_pop : 1
"""


def reset_code(prior_drift: bool = False, prior_repulsion: bool = False, lability: bool = False) -> str:
    code = RESET_CODE
    if prior_drift:
        code += "; creb = creb*(1 - creb_erosion)"          # erosion PER USE, independent of any synaptic rate
    if prior_repulsion:
        code += "; u_use += use_per_spike"
    if lability:
        code += "; lab = lab + (1 - lab)*int(rec_lp > ff_lp)"   # reactivation = a spike driven by recurrence
    return code


def equations(nm_excitability: bool = False, ephaptic: bool = False, *, intrinsic_trace: bool = False,
              prior_repulsion: bool = False, mismatch: bool = False, lability: bool = False,
              provenance: bool = False) -> str:
    """Every optional mechanism adds TEXT only when it is on. With all of them off the equation text is
    byte-identical to the model the published results came from (pinned by hash in tests/test_retrieval.py), so
    the generated code -- and every spike -- is too. Multiplying by a 1.0 gain instead would change the
    expression tree, and under -ffast-math that is enough to diverge a chaotic network."""
    ahp, vt, extra = "", "", ""
    if nm_excitability:
        ahp += "ahp_scale*"; vt += " - k_vt*nm_x"; extra += NM_EXC_EQS
    if intrinsic_trace:
        ahp += "tr_ahp*"; vt += " - k_tr_vt*clip(creb, 0, 1)"; extra += TRACE_EQS
    if prior_repulsion:
        vt += " + k_rep*clip(u_use, 0, 1)"; extra += REPULSION_EQS
    if mismatch or lability:
        extra += CURRENT_TRACE_EQS
    # C5 (provenance) adds NOTHING to the equations: it records g_ext, g_e and V at each spike and the
    # currents are formed in analysis. `provenance` is accepted so the call site documents the intent.
    if mismatch:
        extra += MISMATCH_EQS
    if lability:
        extra += LABILITY_EQS
    if ephaptic:
        extra += EPH_EQS
    return (EQUATIONS.replace("__EPH__", " + I_eph" if ephaptic else "").replace("__AHP__", ahp).replace("__VTNM__", vt) + extra)


RESET_CODE = "V = V_reset; w += b_adapt; Ca_s += Ca_spike"
THRESHOLD = "V > V_cut"


def namespace(p: NeuronParams, cfg: Config, kind: str) -> dict:
    """Constants for one population. ``kind`` is 'exc' or 'inh'."""
    F = cfg.time_compression
    m = cfg.mechanisms
    net, pl, cr, nm = cfg.network, cfg.plasticity, cfg.creb, cfg.neuromod
    k_in = net.p_conn * net.n_exc
    theta_scale = (k_in / pl.indegree_ref) if pl.scale_theta_pro_by_indegree else 1.0
    return dict(
        C=p.C_pF * pF, gL=p.gL_nS * nS, EL=p.EL_mV * mV, VT=p.VT_mV * mV, DeltaT=p.DeltaT_mV * mV,
        V_cut=p.V_cut_mV * mV, V_reset=p.V_reset_mV * mV, a=p.a_nS * nS, b_adapt=p.b_pA * pA,
        tau_w=p.tau_w_ms * ms, E_Ca=p.E_Ca_mV * mV, T_shift=p.T_shift_mV * mV,
        phi_h=3.0 ** ((p.T_celsius - 24.0) / 10.0),
        E_e=net.E_e_mV * mV, E_i=net.E_i_mV * mV, E_K=net.E_K_mV * mV, tau_b=net.tau_b_ms * ms, tau_e=net.tau_e_ms * ms, tau_i=net.tau_i_ms * ms,
        I0=cfg.noise.I0_pA * pA, sigma_bg=cfg.noise.sigma_pA * pA, tau_bg=cfg.noise.tau_ms * ms,
        tau_drift=cfg.drift.tau_s * second,
        sigma_drift=(cfg.drift.sigma_pA if m.tonic_drift else 0.0) * pA,
        k_inh=(nm.k_inh_pA if (kind == "inh" and m.nm_inhibitory_setpoint) else 0.0) * pA, nm_ref=nm.nm_ref,
        k_ahp=cfg.nm_excitability.strength * cfg.nm_excitability.ahp_block_per_nm,
        k_vt=cfg.nm_excitability.strength * cfg.nm_excitability.dVT_mV_per_nm * mV,
        k_tr_ahp=cfg.intrinsic_trace.k_ahp, k_tr_vt=cfg.intrinsic_trace.dVT_mV * mV,
        tau_lab=cfg.lability.tau_s * second,
        tau_mm=cfg.mismatch_gate.tau_ms * ms, mm_eps=cfg.mismatch_gate.eps_pA * pA,
        creb_erosion=cfg.prior_drift.erosion_per_spike, k_rep=cfg.prior_drift.repulsion_mV * mV,
        tau_use=cfg.prior_drift.tau_use_s * second, use_per_spike=cfg.prior_drift.use_per_spike,
        theta_amp=(cfg.theta.amp_pA if cfg.theta.target in (kind, "both") else 0.0) * pA,
        tau_CaT=pl.tau_CaT_ms * ms, k_CaT=pl.k_CaT_per_nA_ms / (nA * ms),
        tau_Cas=cr.tau_Ca_soma_ms * ms, k_T_s=cr.k_T_per_nA_ms / (nA * ms),
        Ca_spike=cr.Ca_spike, creb_on=1.0 if (m.creb and kind == "exc") else 0.0,
        tau_creb=cr.tau_s / F * second, dVT_creb=cr.dVT_mV * mV,
        alpha_p=pl.alpha, tau_p=pl.tau_p_s / F * second,
        nm_dep=1.0, theta_pro_scale=theta_scale, theta_pro_const=pl.theta_pro_default * theta_scale,
        rank_window=cfg.decode.rank_window_ms * ms,
        t_spike_w=p.t_spike_ms * ms, t_reset_w=p.t_reset_ms * ms, hT_loaded=p.hT_loaded,
    )


def make_group(n: int, p: NeuronParams, cfg: Config, kind: str, NM: b2.TimedArray,
               noise_scale: b2.TimedArray, name: str, rng: np.random.Generator,
               theta: b2.TimedArray | None = None, order: int = 0, nph: b2.TimedArray | None = None) -> b2.NeuronGroup:
    ns = namespace(p, cfg, kind)
    ns.update(NM=NM, noise_scale=noise_scale, theta=theta if theta is not None else constant_array(0.0))
    on = cfg.mechanisms.nm_excitability and kind == "exc"
    eph = cfg.ephaptic.g_eph_nS > 0          # g_eph = 0 -> the term is ABSENT, so the generated code is unchanged
    if eph:
        ns.update(g_eph=cfg.ephaptic.g_eph_nS * nS, nph=nph if nph is not None else constant_array(0.0))
    exc = kind == "exc"
    mech = cfg.mechanisms
    g = b2.NeuronGroup(n, equations(on, eph, intrinsic_trace=mech.intrinsic_trace and exc, prior_repulsion=mech.prior_repulsion and exc,
                                          mismatch=mech.mismatch_gate and exc, lability=mech.lability_window and exc,
                                          provenance=cfg.sim.log_provenance and exc),
                       threshold=THRESHOLD, reset=reset_code(mech.prior_drift and exc, mech.prior_repulsion and exc, mech.lability_window and exc),
                       refractory=p.t_ref_ms * ms, method="euler", namespace=ns, name=name, order=order)
    g.V = (p.EL_mV + rng.uniform(0, 8, n)) * mV
    g.hT = 0.01
    g.I_bg = cfg.noise.I0_pA * pA
    g.gT = (p.gT_nS if cfg.mechanisms.t_current else 0.0) * nS
    return g


def constant_array(value: float) -> b2.TimedArray:
    return b2.TimedArray(np.array([value, value]), dt=1e6 * second)


def annotate_bursts(spike_times_s: np.ndarray, max_isi_s: float = 0.010, min_spikes: int = 3):
    """Post hoc burst annotation: runs of >= min_spikes spikes with every ISI <= max_isi.

    Returns a list of (t_first, t_last, n_spikes).
    """
    t = np.sort(np.asarray(spike_times_s, dtype=float))
    bursts, start = [], 0
    for k in range(1, t.size + 1):
        if k == t.size or t[k] - t[k - 1] > max_isi_s:
            if k - start >= min_spikes:
                bursts.append((t[start], t[k - 1], k - start))
            start = k
    return bursts
