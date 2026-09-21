"""R2/R3 -- reproduce Luboeinski & Tetzlaff 2021 (Commun Biol 4:275) INSIDE the neurotape harness. No audio.

Target, protocol, metrics and the pre-registered pass criteria are in docs/repro/TARGET.md (written first).
This module uses neurotape's OWN neuron (neurons/model.py), plasticity and tagging-and-capture code
(plasticity/stc.py), inhibition, gap junctions, noise and time compression. The front end is off: the assembly is
stimulated DIRECTLY, as the paper does -- an Ornstein-Uhlenbeck CURRENT (their Eq. 16) into the cell's `I_inj`.

Protocol (paper / reference code): 1600 E + 400 I, p = 0.1; settle 10 s; three 0.1 s learning pulses at t = 10.0,
10.5, 11.0 s to the first 150 E cells; a 0.1 s recall cue to 75 of them, 10 s after learning (t = 20.0 s) or 8 h after
(t = 28 810 s). As in the paper the 8 h run never sees the 10 s cue: they are two runs from one seed, identical up to
t = 20 s. Cued cells are the first 75 of the assembly -- wiring is random, so this is a random half.

DIFFERENCES between neurotape-as-is and the paper (listed BEFORE any run; docs/repro/DIFFERENCES.md has the prose).
Each key of VARIANTS removes ONE of them:
  adaptation     AdEx spike-triggered + subthreshold adaptation (a, b, tau_w)          paper: none
  t_current      T-type Ca current AND its calcium added to every synapse's calcium    paper: none
  gaba_b         slow GABA_B-like K+ conductance on I->E                                paper: none
  gap            gap junctions among I cells                                            paper: none
  slow           slow OU drift + theta pacemaker + CREB-like excitability               paper: none
  theta_pro      theta_pro = h_0/(NM + 0.001) at tonic NM 0.12  (= 8.3 h_0)             paper: 0.5 h_0, constant
  pl_clock       plasticity ODEs on a 1 ms clock                                        paper: the neuron step
  fast_forward   8 h = 480 s of FULL SPIKING with slow terms sped up 60x                paper: no spiking between
                                                                                        stimuli, slow terms integrated
  inhibition     w_ie = w_ii = 8 g0 (conductance-based, reversal -80 mV)                paper: 4 h_0, current-based
  lif            the whole neuron + synapse model (conductance AdEx, its noise)          paper: current-based LIF
"""
from __future__ import annotations

import numpy as np

from ..config import Config
from . import common as C

N_EXC, N_INH, N_CA, N_CUE = 1600, 400, 150, 75
T_LEARN = (10.0, 10.5, 11.0)
T_SNAP_LEARNED = 12.0            # "end of learning": 0.9 s after the last pulse, before any decay that matters
T_CUE_10S = 20.0
CONSOLIDATE_REAL_S = 28790.0     # 20.0 s -> 28 810.0 s in the paper
RATE_WINDOW_S = 0.5              # centred on the read-out time (reference: instFiringRates)
N_STIM, F_STIM = 25, 100.0

VARIANTS = {
    "as_is": {},
    "adaptation": dict(adaptation=False), "t_current": dict(t_current=False), "gaba_b": dict(gaba_b=False),
    "gap": dict(gap=False), "slow": dict(slow=False), "theta_pro": dict(theta_pro_paper=True),
    "pl_clock": dict(pl_clock_neuron=True), "fast_forward": dict(fast_forward=True), "inhibition": dict(inh4=True),
    "lif": dict(lif=True),
}


def base_config(seed: int, v: dict, plasticity: bool = True) -> Config:
    cfg = Config(); cfg.seed = seed
    cfg.network.n_exc, cfg.network.n_inh = N_EXC, N_INH
    assert cfg.plasticity.preset == "luboeinski2021" and cfg.plasticity.theta_p == 3.0 and cfg.plasticity.theta_d == 1.2
    m = cfg.mechanisms
    m.plasticity = plasticity
    m.nm_dynamic = False                       # no stimulus envelope exists, so no salience-triggered NM: NM is tonic
    if v.get("adaptation") is False:
        cfg.network.exc.a_nS = 0.0; cfg.network.exc.b_pA = 0.0
    if v.get("t_current") is False:
        m.t_current = False
    if v.get("gaba_b") is False:
        cfg.network.w_ie_b_nS = 0.0
    if v.get("gap") is False:
        m.gap_junctions = False
    if v.get("slow") is False:
        m.tonic_drift = False; m.theta = False; m.creb = False
    if v.get("pl_clock_neuron"):
        cfg.plasticity.update_dt_ms = cfg.sim.dt_ms
    if v.get("inh4"):
        cfg.network.w_ie_nS = 4.0; cfg.network.w_ii_nS = 4.0
    return cfg


# ------------------------------------------------------------------------------------------------------------
# metrics -- exactly the reference's (analysis/calculateQ.py, calculateMIa.py, valueDistributions.py; Apache-2.0,
# re-implemented). Rates are spike counts in a 0.5 s window, so they are discrete and the entropies are plug-in
# estimates over the occurring values, with no binning.
# ------------------------------------------------------------------------------------------------------------
def window_rates(i, t, t_read, n):
    k = (t >= t_read - RATE_WINDOW_S / 2) & (t < t_read + RATE_WINDOW_S / 2)
    return np.bincount(i[k], minlength=n)[:n] / RATE_WINDOW_S


def _entropy(rows):
    _, c = np.unique(rows, return_counts=True, axis=0); p = c / c.sum()
    return float(-(p * np.log2(p)).sum())


def mutual_information(v_ref, v_recall):
    return _entropy(v_ref[:, None]) + _entropy(v_recall[:, None]) - _entropy(np.stack([v_ref, v_recall], axis=1))


def q_star(v, cued, ans, ctrl):
    nu_as, nu_ans, nu_ctrl = v[cued].mean(), v[ans].mean(), v[ctrl].mean()
    return dict(nu_as=float(nu_as), nu_ans=float(nu_ans), nu_ctrl=float(nu_ctrl),
                Q=float((nu_ans - nu_ctrl) / nu_as) if nu_as > 0 else float("nan"))


def tag_counts(h, z, n_ca, theta_tag, syn_i, syn_j):
    """D2-style: tags by sign, over all E->E and within the assembly. A tag is |h - h_0| > theta_tag (h_0 = 1 here)."""
    ca = (syn_i < n_ca) & (syn_j < n_ca)
    out = {}
    for name, sel in (("all", np.ones(h.size, bool)), ("within_assembly", ca), ("outside_assembly", ~ca)):
        d = h[sel] - 1.0
        out[name] = dict(n=int(sel.sum()), tag_pot=int((d > theta_tag).sum()), tag_dep=int((d < -theta_tag).sum()),
                         late_pot=int((z[sel] > 0.01).sum()), late_dep=int((z[sel] < -0.01).sum()),
                         mean_h=float(h[sel].mean()), mean_z=float(z[sel].mean()), mean_w=float((h[sel] + z[sel]).mean()))
    return out


# ------------------------------------------------------------------------------------------------------------
# one run
# ------------------------------------------------------------------------------------------------------------
def simulate(seed: int, recall: str, variant: str = "as_is", cue: str = "assembly", plasticity: bool = True,
             consolidate_sim_s: float | None = None, n_exc: int = N_EXC, n_inh: int = N_INH) -> dict:
    """recall: '10s' or '8h'. cue: 'assembly' (first 75 assembly cells) or 'shuffled' (75 never-learned cells)."""
    import time as _time
    import brian2 as b2
    from brian2 import ms, mV, nS, pA, nA, second
    from ..network import _activate, _worker_build_dir
    from ..neurons import model as nmodel
    from ..plasticity import stc
    from ..coupling import gap as gapmod
    from ..neuromod.theta import THETA_DT_S, build_theta

    t_wall = _time.time()
    v = VARIANTS[variant]
    if v.get("lif"):
        raise NotImplementedError("the LIF variant is built only if the ladder needs it")
    cfg = base_config(seed, v, plasticity)
    cfg.network.n_exc, cfg.network.n_inh = n_exc, n_inh
    F = cfg.time_compression
    n_ca = max(int(round(N_CA * n_exc / N_EXC)), 4); n_cue = n_ca // 2
    rng = np.random.default_rng(seed)
    _activate(cfg, _worker_build_dir(None)); bd = _worker_build_dir(None)
    b2.seed(seed); b2.defaultclock.dt = cfg.sim.dt_ms * ms
    net_c, mech = cfg.network, cfg.mechanisms

    cons = (CONSOLIDATE_REAL_S / F) if consolidate_sim_s is None else consolidate_sim_s
    ff = bool(v.get("fast_forward")) and recall == "8h"
    t_cue = T_CUE_10S if recall == "10s" else round(T_CUE_10S + cons, 1)
    total = t_cue + 0.6
    # ---- gates on a 0.1 s grid (every stimulus edge lies on it) ----
    n_g = int(round(total / 0.1)) + 2
    g_learn, g_cue, g_quiet = np.zeros(n_g), np.zeros(n_g), np.ones(n_g)
    for tl_ in T_LEARN:
        g_learn[int(round(tl_ / 0.1))] = 1.0
    g_cue[int(round(t_cue / 0.1))] = 1.0
    if ff:       # the paper's fast-forward: NO spiking between the stimuli -- background held off, then a 10 s re-settle
        g_quiet[int(round((T_CUE_10S + 0.1) / 0.1)):int(round((t_cue - 10.0) / 0.1))] = 0.0
    GL = b2.TimedArray(g_learn, dt=0.1 * second, name="ta_glearn"); GC = b2.TimedArray(g_cue, dt=0.1 * second, name="ta_gcue")
    NM = b2.TimedArray(np.full(2, cfg.neuromod.tonic), dt=1e6 * second, name="ta_nm")
    NS = b2.TimedArray(g_quiet, dt=0.1 * second, name="ta_noise")
    th_t, th, _ = build_theta(cfg, total, np.array([]), seed)
    THETA = b2.TimedArray(th, dt=THETA_DT_S * second, name="ta_theta")

    E = nmodel.make_group(n_exc, net_c.exc, cfg, "exc", NM, NS, "exc", rng, THETA, order=0)
    I = nmodel.make_group(n_inh, net_c.inh, cfg, "inh", NM, NS, "inh", rng, THETA, order=1)
    if v.get("theta_pro_paper"):
        E.namespace["nm_dep"] = 0.0                       # theta_pro = theta_pro_default (0.5 h_0) x in-degree scale (1 here)

    # ---- direct stimulation, Eq. 16: OU current, mean N f w, SD w sqrt(N f / (2 tau)), tau = tau_syn. The weight w is
    # neurotape's h_0-equivalent: one unit synapse, g0 x (E_e - E_L), as a current. Like the paper's, it is large enough
    # that stimulated cells fire at their refractory limit. ----
    w_unit = net_c.g0_nS * nS * (net_c.E_e_mV - net_c.exc.EL_mV) * mV
    tau = net_c.tau_e_ms * ms
    mu = N_STIM * F_STIM * w_unit
    sd = w_unit * np.sqrt(N_STIM * F_STIM) / np.sqrt(2 * float(tau / second))
    k_ou = float(np.exp(-cfg.sim.dt_ms * ms / tau)); s_ou = sd * np.sqrt(1 - k_ou ** 2)
    stim_ns = dict(mu_s=mu, k_ou=k_ou, s_ou=s_ou, GL=GL, GC=GC, dt_s=cfg.sim.dt_ms * ms)
    code = "I_inj = G*(mu_s + Gp*(I_inj - mu_s)*k_ou + s_ou*randn())"
    groups = {"cued": (slice(0, n_cue), "(GL(t) + GC(t))", "(GL(t - dt_s) + GC(t - dt_s))"),
              "ans": (slice(n_cue, n_ca), "GL(t)", "GL(t - dt_s)")}
    if cue == "shuffled":
        groups["cued"] = (slice(0, n_cue), "GL(t)", "GL(t - dt_s)")
        groups["shuf"] = (slice(n_ca, n_ca + n_cue), "GC(t)", "GC(t - dt_s)")
    stim_ops = []
    for k_, (name, (sl, g_now, g_prev)) in enumerate(groups.items()):
        sub = E[sl]
        stim_ops.append(sub.run_regularly(code.replace("Gp", g_prev).replace("G*", g_now + "*"), when="start", order=10 + k_, name=f"stim_{name}"))
        sub.namespace.update(stim_ns) if hasattr(sub, "namespace") else None
    E.namespace.update(stim_ns)
    if ff:
        # background MEAN off as well while fast-forwarding (noise SD is already gated by ta_noise)
        E.run_regularly("I_bg = I_bg*NSq(t)", when="start", order=20, name="ff_e"); I.run_regularly("I_bg = I_bg*NSq(t)", when="start", order=21, name="ff_i")
        E.namespace["NSq"] = NS; I.namespace["NSq"] = NS

    def rand_conn(n_pre, n_post, p, no_self=False):
        m_ = rng.random((n_pre, n_post)) < p
        if no_self:
            np.fill_diagonal(m_, False)
        return np.nonzero(m_)

    S_ee = b2.Synapses(E, E, stc.plastic_model(cfg), on_pre=stc.ON_PRE, on_post=stc.ON_POST, delay=stc.delays(cfg), method="heun",
                       namespace=stc.namespace(cfg), dt=cfg.plasticity.update_dt_ms * ms, name="ee", order=2)
    ee_i, ee_j = rand_conn(n_exc, n_exc, net_c.p_conn, True); S_ee.connect(i=ee_i, j=ee_j); S_ee.h = 1.0; S_ee.z = 0.0
    ax = net_c.axon_delay_ms * ms
    S_ei = b2.Synapses(E, I, on_pre="g_e_post += w_syn", namespace=dict(w_syn=net_c.w_ei_nS * nS), delay=ax, name="ei")
    a_, b_ = rand_conn(n_exc, n_inh, net_c.p_conn); S_ei.connect(i=a_, j=b_)
    S_ie = b2.Synapses(I, E, on_pre="g_i_post += w_syn; g_b_post += w_b", namespace=dict(w_syn=net_c.w_ie_nS * nS, w_b=net_c.w_ie_b_nS * nS), delay=ax, name="ie")
    a_, b_ = rand_conn(n_inh, n_exc, net_c.p_conn); S_ie.connect(i=a_, j=b_)
    S_ii = b2.Synapses(I, I, on_pre="g_i_post += w_syn", namespace=dict(w_syn=net_c.w_ii_nS * nS), delay=ax, name="ii")
    a_, b_ = rand_conn(n_inh, n_inh, net_c.p_conn, True); S_ii.connect(i=a_, j=b_)
    objs = [E, I, S_ee, S_ei, S_ie, S_ii] + stim_ops
    if mech.gap_junctions:
        pairs = gapmod.ring_pairs(n_inh, cfg.gap.neighbourhood, cfg.gap.p, rng)
        objs.append(gapmod.make_gap(I, pairs, gapmod.conductance_for_cc(cfg.gap.coupling_coefficient, net_c.inh.gL_nS), cfg.gap.modulation, "gap_ii"))
    k_order = 0
    for syn in [o for o in objs if isinstance(o, b2.Synapses)]:
        for pw in syn._pathways:
            pw.order = k_order; k_order += 1
    sm_e = b2.SpikeMonitor(E, name="sp_e"); sm_i = b2.SpikeMonitor(I, name="sp_i")
    snap = b2.StateMonitor(S_ee, ["h", "z"], record=True, dt=0.1 * second, when="start", name="snap")
    snap_p = b2.StateMonitor(E, "p", record=True, dt=0.1 * second, when="start", name="snap_p")
    objs += [sm_e, sm_i, snap, snap_p]
    net = b2.Network(*objs)

    instants = {"pre_learning": T_LEARN[0], "end_of_learning": T_SNAP_LEARNED, "pre_10s_recall": T_CUE_10S}
    if recall == "8h":
        instants["pre_8h_recall"] = t_cue
    edges = sorted({0.0, total} | set(instants.values()) | {round(x + 0.1, 1) for x in instants.values()})
    for a, b in zip(edges[:-1], edges[1:]):
        snap.active = snap_p.active = any(abs(a - x) < 1e-9 for x in instants.values())
        net.run((b - a) * second)
    if cfg.sim.device == "cpp_standalone":
        b2.device.build(directory=str(bd), compile=True, run=False, debug=False, clean=False)
        b2.device.run(str(bd), with_output=False, run_args=[])

    i, t = np.array(sm_e.i), np.array(sm_e.t / second)
    st = np.array(snap.t / second); H, Z, P = np.array(snap.h), np.array(snap.z), np.array(snap_p.p)
    assert st.size == len(instants), (st, instants)
    cued = np.arange(0, n_cue) if cue == "assembly" else np.arange(n_ca, n_ca + n_cue)
    ans = np.arange(n_cue, n_ca) if cue == "assembly" else np.arange(0, n_ca)        # shuffled cue: the WHOLE stored assembly is "not cued"
    never = np.setdiff1d(np.arange(n_exc), np.concatenate([np.arange(n_ca), cued]))
    ctrl_assembly = np.random.default_rng(seed + 4242).choice(never, n_cue, replace=False)
    v_rec = window_rates(i, t, t_cue + 0.1, n_exc); v_learn = window_rates(i, t, 11.0, n_exc)
    v_standby = np.bincount(i[(t >= 5.0) & (t < 10.0)], minlength=n_exc) / 5.0
    out = dict(seed=seed, recall=recall, variant=variant, cue=cue, plasticity=plasticity, t_cue=t_cue, F=F, wall_s=_time.time() - t_wall,
               **q_star(v_rec, cued, ans, never), MI=mutual_information(v_learn, v_rec),
               nu_control_assembly=float(v_rec[ctrl_assembly].mean()),
               rate_learning_pulse_hz=float(((t >= 10.0) & (t < 10.1) & (i < n_ca)).sum() / n_ca / 0.1),
               rate_cue_pulse_hz=float(((t >= t_cue) & (t < t_cue + 0.1) & np.isin(i, cued)).sum() / cued.size / 0.1),
               standby_e_hz=float(v_standby.mean()), standby_i_hz=float((np.array(sm_i.t / second) < 10.0).sum() / n_inh / 10.0),
               consolidation_e_hz=float(((t >= 30.0) & (t < t_cue - 10.0)).sum() / n_exc / max(t_cue - 40.0, 1e-9)) if recall == "8h" else None,
               tags={name: tag_counts(H[:, k], Z[:, k], n_ca, cfg.plasticity.theta_tag, ee_i, ee_j) for k, name in enumerate(instants)},
               protein={name: dict(assembly=float(P[:n_ca, k].mean()), rest=float(P[n_ca:, k].mean())) for k, name in enumerate(instants)},
               learn_spike_hash=int(np.round(t[t < T_CUE_10S] * 1e5).astype(np.int64).sum() % (2 ** 31)))
    return out


def _worker(job):
    try:
        return dict(ok=True, tag=job.pop("tag"), **simulate(**job))
    except Exception as e:
        import traceback
        return dict(ok=False, tag=job.get("tag"), seed=job.get("seed"), error=f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-1200:])


PAPER = dict(Q={"10s": (0.0303, 0.0029), "8h": (0.0349, 0.0037)}, MI={"10s": (0.8742, 0.0346), "8h": (0.9759, 0.0231)})


def score(runs_10s, runs_8h, n_expected=10):
    """The three pre-registered criteria of docs/repro/TARGET.md, applied to one condition."""
    out, vals = {}, {}
    for key, rs in (("10s", runs_10s), ("8h", runs_8h)):
        ok = [r for r in rs if r.get("ok")]
        vals[key] = dict(Q=[r["Q"] for r in ok], MI=[r["MI"] for r in ok])
        for mname in ("Q", "MI"):
            x = np.array(vals[key][mname], float); m, s = PAPER[mname][key]
            out[f"{mname}_{key}"] = dict(mean=float(np.nanmean(x)) if x.size else float("nan"), sd=float(np.nanstd(x, ddof=1)) if x.size > 1 else float("nan"),
                                         n=int(x.size), paper_mean=m, paper_sd=s, lo=m - s, hi=m + s,
                                         within=bool(x.size and m - s <= np.nanmean(x) <= m + s))
        n_b = sum(1 for r in ok if r["nu_ans"] > r["nu_control_assembly"])
        out[f"b_{key}"] = dict(n_pass=n_b, n=n_expected, passed=bool(n_b >= 8))
    out["a_pass"] = all(out[f"{m}_{k}"]["within"] for m in ("Q", "MI") for k in ("10s", "8h"))
    out["b_pass"] = out["b_10s"]["passed"] and out["b_8h"]["passed"]
    gq = out["Q_8h"]["mean"] / out["Q_10s"]["mean"] - 1 if out["Q_10s"]["mean"] else float("nan")
    gm = out["MI_8h"]["mean"] / out["MI_10s"]["mean"] - 1 if out["MI_10s"]["mean"] else float("nan")
    out["gain_Q"], out["gain_MI"] = float(gq), float(gm)
    out["c_pass"] = bool(out["Q_8h"]["mean"] > out["Q_10s"]["mean"] and out["MI_8h"]["mean"] > out["MI_10s"]["mean"])
    return out


def run_condition(name, seeds, workers, **kw):
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import get_context
    jobs = [dict(tag=f"{name}|{rc}", seed=int(s), recall=rc, **kw) for rc in ("8h", "10s") for s in seeds]
    with ProcessPoolExecutor(max(workers, 1), mp_context=get_context("spawn")) as ex:
        runs = list(ex.map(_worker, jobs))
    return runs


# ------------------------------------------------------------------------------------------------------------
# the experiment: conditions are run in stages and each is stored on its own, so a long stage never re-runs a
# finished one. `neurotape exp repro_lt2021` runs whatever NEUROTAPE_REPRO_STAGE names (default: as_is).
# ------------------------------------------------------------------------------------------------------------
RUNS_DIR = C.ROOT / "docs" / "repro" / "runs"

STAGES = {
    "as_is": [("as_is", dict(variant="as_is"), ("8h", "10s"))],
    "ladder10s": [(f"ladder:{k}", dict(variant=k), ("10s",)) for k in VARIANTS if k not in ("as_is", "lif", "fast_forward")],
    "controls": [("ctrl:plasticity_off", dict(variant="as_is", plasticity=False), ("8h", "10s")),
                 ("ctrl:shuffled_cue", dict(variant="as_is", cue="shuffled"), ("8h", "10s"))],
    "controls10s": [("ctrl:plasticity_off", dict(variant="as_is", plasticity=False), ("10s",)),
                    ("ctrl:shuffled_cue", dict(variant="as_is", cue="shuffled"), ("10s",))],
}


def run_stage(stage: str, seeds, workers: int, extra: list | None = None):
    import json
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import get_context
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    conds = (extra or []) + STAGES.get(stage, [])
    jobs = []
    for name, kw, recalls in conds:
        for rc in recalls:                       # long (8 h) jobs are queued first
            f = RUNS_DIR / f"{name.replace(':', '_')}__{rc}.json"
            if f.exists():
                continue
            jobs += [dict(tag=f"{name}|{rc}", seed=int(s), recall=rc, **kw) for s in seeds]
    jobs.sort(key=lambda j: j["recall"] != "8h")
    with ProcessPoolExecutor(max(workers, 1), mp_context=get_context("spawn")) as ex:
        runs = list(ex.map(_worker, jobs))
    by = {}
    for r in runs:
        by.setdefault(r["tag"], []).append(r)
    for tag, rs in by.items():
        name, rc = tag.split("|")
        (RUNS_DIR / f"{name.replace(':', '_')}__{rc}.json").write_text(json.dumps(rs, indent=1, default=float))
    return by


def exp_repro_lt2021(cfg: Config, seeds, workers):
    import os
    stage = os.environ.get("NEUROTAPE_REPRO_STAGE", "as_is")
    run_stage(stage, seeds, workers)
    return RUNS_DIR
