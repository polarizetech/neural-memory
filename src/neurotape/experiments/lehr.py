"""Experiment 5 -- reproduce the Lehr, Luboeinski & Tetzlaff 2022 neuromodulator sweep BEFORE extending it.

This is the REFERENCE model, not neurotape's: current-based leaky integrate-and-fire neurons, the
published plasticity/STC equations (plasticity/stc.py documents them), a 150-of-1600 core
assembly given three 100 ms learning pulses, consolidation under a CONSTANT neuromodulator level,
and recall by one pulse to half the core. Equations and constants from jlubo/brian_network_plasticity
(config_defaultnet.json) and jlubo/memory-consolidation-stc (theta_pro = h_0/(NM + 0.001)).

Deviations from the published runs, all forced by cost and all stated in the report:
  * network size is reduced (default 400 E / 100 I, core 38) with theta_pro scaled by in-degree/160;
  * 8 h of consolidation is simulated with the 60x time compression of the slow terms instead of
    the authors' analytic fast-forward;
  * plasticity ODEs run on a 1 ms clock;
  * the learning-stimulus amplitude is taken literally from the Brian2 reference and was not
    cross-checked against the C++ implementation.

PASS CRITERIA -- written here before the sweep was ever run, from the paper's Results text:
  C1  NM = 0: no consolidation anywhere (mean late weight z of core-internal AND outgoing < 0.02).
  C2  core-internal synapses consolidate already at LOW NM (0.06): mean total weight > 150% of h_0.
  C3  outgoing synapses need HIGHER NM: mean outgoing z rises monotonically with NM (Spearman
      rho > 0.8 across the sweep) and at NM = 0.06 outgoing total weight < core-internal.
  C4  activity OUTSIDE the core during 8 h recall rises with NM (Spearman rho > 0.8).
"""
from __future__ import annotations


import numpy as np
from scipy import stats

from ..config import Config
from ..plasticity import stc
from . import common as C

NM_LEVELS = (0.0, 0.03, 0.06, 0.12, 0.18, 0.24)


def simulate_reference(nm: float, seed: int, n_exc=400, n_inh=100, consolidate_s=480.0, F=60.0,
                       device="cpp_standalone") -> dict:
    import brian2 as b2
    from brian2 import ms, mV, second, nA, Mohm, Hz
    cfg = Config(); cfg.time_compression = F; cfg.mechanisms.t_current = False
    rng = np.random.default_rng(seed)
    from ..network import _worker_build_dir
    import gc
    gc.collect()
    bd = _worker_build_dir(None)                 # reused per worker: incremental compiles
    if device == "cpp_standalone":
        b2.device.reinit(); b2.set_device("cpp_standalone", build_on_run=False, directory=str(bd))
        b2.device.activate(build_on_run=False, directory=str(bd))
        b2.prefs["devices.cpp_standalone.extra_make_args_unix"] = ["-j3"]   # Brian2's default is a bare, unbounded -j
    else:
        b2.set_device("runtime"); b2.prefs.codegen.target = "numpy"
    b2.start_scope(); b2.seed(seed); b2.defaultclock.dt = 0.2 * ms
    h0 = 4.20075 * mV
    n_core = max(int(round(n_exc * 150 / 1600)), 4)
    k_in = 0.1 * n_exc
    t_learn, t_rec10 = 2.0, 2.0 + 1.1 + 10.0
    t_rec8h = t_rec10 + 0.1 + consolidate_s
    total = t_rec8h + 0.5
    ns = dict(tau_mem=10 * ms, V_rev=-65 * mV, V_reset=-70 * mV, V_th=-55 * mV, R_mem=10 * Mohm, tau_syn=5 * ms,
              tau_OU=5 * ms, I_0=0.15 * nA, sigma_wn=0.05 * nA * second ** 0.5, h_0=h0, N_stim=25, f_stim=100 * Hz,
              alpha_p=1.0, tau_p=3600.0 / F * second, theta_pro=(k_in / 160.0) / (nm + 0.001),
              t_l=t_learn * second, t_a=t_rec10 * second, t_b=t_rec8h * second)
    neuron = """
    dV/dt = (-(V - V_rev) + V_psp + R_mem*I_bg + stim_on*V_stim)/tau_mem : volt (unless refractory)
    dI_bg/dt = (-I_bg + I_0 + sigma_wn*xi_bg)/tau_OU : amp
    dV_psp/dt = -V_psp/tau_syn : volt
    dV_stim/dt = (-V_stim + (N_stim*f_stim + sqrt(N_stim*f_stim)*xi_stim)*second*h_0)/tau_OU : volt
    stim_on = is_core*(int(t >= t_l and t <= t_l + 0.1*second) + int(t >= t_l + 0.5*second and t <= t_l + 0.6*second)
              + int(t >= t_l + 1.0*second and t <= t_l + 1.1*second))
              + is_cue*(int(t >= t_a and t <= t_a + 0.1*second) + int(t >= t_b and t <= t_b + 0.1*second)) : 1
    is_core : 1 (constant)
    is_cue : 1 (constant)
    dp/dt = (-p + alpha_p*int(sum_h_diff > theta_pro))/tau_p : 1
    sum_h_diff : 1
    CaT : 1
    """
    E = b2.NeuronGroup(n_exc, neuron, threshold="V > V_th", reset="V = V_reset", refractory=2 * ms, method="heun", namespace=ns, name="E")
    I = b2.NeuronGroup(n_inh, neuron, threshold="V > V_th", reset="V = V_reset", refractory=2 * ms, method="heun", namespace=ns, name="I")
    for g in (E, I):
        g.V = -65 * mV; g.I_bg = 0.15 * nA
    E.is_core[:n_core] = 1; E.is_cue[:n_core // 2] = 1
    pns = stc.namespace(cfg); pns["h_0"] = h0
    on_pre = {"pre_v": "V_psp_post += h_0*clip(h + z, 0, 10)", "pre_ca": "Ca += Ca_pre*plastic_on"}
    S = b2.Synapses(E, E, stc.PLASTIC_MODEL, on_pre=on_pre, on_post=stc.ON_POST, delay={"pre_v": 3 * ms, "pre_ca": 18.8 * ms},
                    method="heun", namespace=pns, dt=1 * ms, name="ee")
    m = rng.random((n_exc, n_exc)) < 0.1; np.fill_diagonal(m, False); si, sj = np.nonzero(m)
    S.connect(i=si, j=sj); S.h = 1.0
    objs = [E, I, S]
    for name, a, bgrp, w in (("ei", E, I, 2.0), ("ie", I, E, -4.0), ("ii", I, I, -4.0)):
        syn = b2.Synapses(a, bgrp, on_pre="V_psp_post += w_s", namespace=dict(w_s=w * h0), delay=3 * ms, name=name)
        mm = rng.random((len(a), len(bgrp))) < 0.1
        if a is bgrp:
            np.fill_diagonal(mm, False)
        ii, jj = np.nonzero(mm); syn.connect(i=ii, j=jj); objs.append(syn)
    sp = b2.SpikeMonitor(E, name="sp"); objs.append(sp)
    net = b2.Network(*objs); net.run(total * second)
    if device == "cpp_standalone":
        b2.device.build(directory=str(bd), compile=True, run=False, debug=False, clean=False)
        b2.device.run(str(bd), with_output=False, run_args=[])
    h, z = np.array(S.h[:]), np.array(S.z[:]); t, i = np.array(sp.t / second), np.array(sp.i)
    core_int = (si < n_core) & (sj < n_core); outgoing = (si < n_core) & (sj >= n_core)
    rec = (t >= t_rec8h) & (t < t_rec8h + 0.1)
    out = dict(nm=nm, seed=seed, n_core=n_core, z_core=float(z[core_int].mean()), z_out=float(z[outgoing].mean()),
               w_core=float((h + z)[core_int].mean()), w_out=float((h + z)[outgoing].mean()),
               rate_outside_recall8h=float((rec & (i >= n_core)).sum() / max(n_exc - n_core, 1) / 0.1),
               rate_core_learn=float(((t >= t_learn) & (t < t_learn + 0.1) & (i < n_core)).sum() / n_core / 0.1))
    return out


def _worker(job):
    try:
        return dict(ok=True, tag=f"nm{job['nm']}", **simulate_reference(**job))
    except Exception as e:
        import traceback
        return dict(ok=False, tag=f"nm{job['nm']}", seed=job["seed"], error=f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-900:])


def exp_lehr(cfg: Config, seeds, workers, n_exc=400, n_inh=100, consolidate_s=480.0):
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import get_context
    out = C.results_dir("exp5_lehr_nm_sweep")
    jobs = [dict(nm=nm, seed=int(s), n_exc=n_exc, n_inh=n_inh, consolidate_s=consolidate_s, F=cfg.time_compression)
            for nm in NM_LEVELS for s in seeds]
    with ProcessPoolExecutor(max(workers, 1), mp_context=get_context("spawn")) as ex:
        runs = list(ex.map(_worker, jobs))
    ok = [r for r in runs if r["ok"]]
    agg = {nm: {k: C.ci95([r[k] for r in ok if r["nm"] == nm]) for k in ("z_core", "z_out", "w_core", "w_out", "rate_outside_recall8h", "rate_core_learn")}
           for nm in NM_LEVELS}
    mean = lambda k: [agg[nm][k]["mean"] for nm in NM_LEVELS]
    c1 = agg[0.0]["z_core"]["mean"] < 0.02 and agg[0.0]["z_out"]["mean"] < 0.02
    c2 = agg[0.06]["w_core"]["mean"] > 1.5
    rho_out = stats.spearmanr(NM_LEVELS, mean("z_out"))[0]
    c3 = bool(rho_out > 0.8 and agg[0.06]["w_out"]["mean"] < agg[0.06]["w_core"]["mean"])
    rho_act = stats.spearmanr(NM_LEVELS, mean("rate_outside_recall8h"))[0]
    c4 = bool(rho_act > 0.8)
    verdict = {"C1_no_NM_no_consolidation": bool(c1), "C2_core_consolidates_at_low_NM": bool(c2),
               "C3_outgoing_needs_higher_NM": c3, "C4_outside_activity_rises_with_NM": c4}
    rows = "| NM | core-internal z | outgoing z | core w/h0 | outgoing w/h0 | outside-core rate at 8 h recall (Hz) | core rate in learning pulse (Hz) |\n|---|---|---|---|---|---|---|\n"
    for nm in NM_LEVELS:
        a = agg[nm]; rows += f"| {nm} | " + " | ".join(C.fmt(a[k]) for k in ("z_core", "z_out", "w_core", "w_out", "rate_outside_recall8h", "rate_core_learn")) + " |\n"
    n_pass = sum(verdict.values())
    rep = (f"## Experiment 5 -- Lehr et al. 2022 NM sweep, reproduction attempt\n\nReduced network: {n_exc} E / {n_inh} I; "
           f"{consolidate_s:g} s simulated = {consolidate_s * cfg.time_compression / 3600:.1f} h of slow-process time.\n\n" + rows +
           "\n### Pre-registered criteria\n\n" + "".join(f"- **{k}**: {'PASS' if v else 'FAIL'}\n" for k, v in verdict.items()) +
           "\nThe last column is a check on the STIMULUS, not a result: a core rate at the refractory limit (500 Hz) means the "
           "reference's learning-stimulus amplitude, taken literally, saturates the cells. Unverified against the paper's figures.\n"
           f"\nSpearman rho, outgoing z vs NM: {rho_out:+.2f}; outside-core recall activity vs NM: {rho_act:+.2f}.\n\n"
           f"**{n_pass}/4 criteria pass.** " + (("The published QUALITATIVE pattern is reproduced at this scale." +
                                                (" **But the activity regime is not the paper's**: core cells fire at the refractory limit during "
                                                 "learning, so treat this as a reproduction of the consolidation logic, not of the network dynamics.\n"
                                                 if agg[NM_LEVELS[0]]["rate_core_learn"]["mean"] > 300 else " Extensions may build on it.\n"))
                                               if n_pass == 4 else "The reproduction is INCOMPLETE: results from the extended model should not be "
                                               "described as building on Lehr et al. until the failing criteria are understood.\n"))
    C.save(out, cfg, runs, dict(aggregate={str(k): v for k, v in agg.items()}, verdict=verdict), rep)
    return out
