"""Assemble the network, run the whole timeline once, and return what was recorded.

Layout: a Poisson input layer (rates = mixed band envelopes x NM gain) -> E cells (plastic E->E with
calcium/STC) <-> I cells (gap-coupled). Competition is lateral inhibition through the I pool; there
is no algorithmic winner-take-all anywhere.
"""
from __future__ import annotations

import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import brian2 as b2
from brian2 import ms, mV, nS, pA, amp, second, Hz

from .config import Config
from .coupling import gap as gapmod
from .frontend.encode import Inputs, build_inputs  # noqa: F401  (re-exported)
from .neuromod.nm import NM_DT_S, NMTrace, build_nm
from .neuromod.theta import THETA_DT_S, build_theta, envelope_onsets
from .neurons import model as nmodel
from .plasticity import stc
from .recall.protocol import Timeline, build_timeline


@dataclass
class RunResult:
    cfg: Config
    timeline: Timeline
    nm: NMTrace
    n_exc: int
    n_inh: int
    spikes_e: tuple[np.ndarray, np.ndarray]      # (i, t_seconds)
    spikes_i: tuple[np.ndarray, np.ndarray]
    state_t: np.ndarray                          # seconds; only where state logging was active
    state_e: np.ndarray                          # (n_exc, n_t) int8 state enum
    state_i: np.ndarray
    rank_t: np.ndarray                           # window END times, seconds
    drive: np.ndarray                            # (n_exc, n_windows) mean excitatory conductance, nS
    slow_t: np.ndarray
    p: np.ndarray                                # (n_exc, n_slow) protein
    creb: np.ndarray
    drift: np.ndarray                            # pA
    w_t: np.ndarray
    h_log: np.ndarray                            # (n_logged_syn, n_w)
    z_log: np.ndarray
    syn_i: np.ndarray
    syn_j: np.ndarray
    h_final: np.ndarray
    z_final: np.ndarray
    spike_Iff: np.ndarray = None                 # C5: per E spike, its own feedforward current (pA); None if off
    spike_Irec: np.ndarray = None                # C5: per E spike, its own recurrent excitatory current (pA)
    lfp_t: np.ndarray = None                     # 1 ms grid, whole timeline
    lfp_Ie: np.ndarray = None                    # pA, summed excitatory synaptic current onto E cells
    lfp_Ii: np.ndarray = None                    # pA, summed inhibitory synaptic current onto E cells
    lfp_Ir: np.ndarray = None                    # pA, summed RECURRENT excitatory current only (no afferent)
    theta_t: np.ndarray = None
    theta: np.ndarray = None
    theta_phase: np.ndarray = None
    onsets_s: np.ndarray = None                  # envelope onsets, timeline clock
    wall_s: float = 0.0
    profile: str = ""
    extra: dict = field(default_factory=dict)


_BUILD_DIR: Path | None = None


_SLOT_LOCK = None


def _worker_build_dir(build_root: Path | None) -> Path:
    """A build SLOT that outlives the process. Every experiment opens a fresh worker pool, and a fresh
    directory per process meant six full rebuilds per experiment (measured: the first six jobs of each
    experiment took ~900 s against ~100 s in steady state). A slot is claimed with a non-blocking flock
    held for the life of the process, so two live workers never share one; the next pool reuses the
    compiled objects. Slots live in the system temp dir and are safe to delete at any time."""
    global _BUILD_DIR, _SLOT_LOCK
    if _BUILD_DIR is None:
        import fcntl
        root = Path(build_root) if build_root else Path(tempfile.gettempdir())
        for k in range(256):
            d = root / f"brian_build_neurotape_slot{k}"
            d.mkdir(parents=True, exist_ok=True)
            fh = open(d / ".slot.lock", "w")
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                fh.close(); continue
            _BUILD_DIR, _SLOT_LOCK = d, fh
            break
    return _BUILD_DIR


def _activate(cfg: Config, build_dir: Path | None):
    if cfg.sim.device == "cpp_standalone":
        b2.device.reinit()
        b2.set_device("cpp_standalone", build_on_run=False, directory=str(build_dir))
        b2.device.activate(build_on_run=False, directory=str(build_dir))
        # Brian2's default `make -j` is UNBOUNDED: one full build launched ~100 clang processes, drove the
        # load average past 200 and starved every running simulation (measured: clang 581 %, sims 16 %).
        b2.prefs["devices.cpp_standalone.extra_make_args_unix"] = ["-j3"]   # (the default is a bare "-j")
    else:
        b2.set_device("runtime")
        b2.prefs.codegen.target = cfg.sim.runtime_target
    import gc
    gc.collect()                                   # release last run's named objects before reusing names
    b2.start_scope()


def simulate(cfg: Config, inputs: Inputs, build_root: Path | None = None) -> RunResult:
    t_wall = time.time()
    rng = np.random.default_rng(cfg.seed)
    build_dir = None
    if cfg.sim.device == "cpp_standalone":
        # ONE build directory per worker process, reused across runs: Brian2 only rewrites source files
        # whose content changed, so `make` recompiles a handful of objects instead of all of them.
        # Measured: a full build is 17-43 s and, being serialised, bounded the whole suite.
        build_dir = _worker_build_dir(build_root)
    _activate(cfg, build_dir)
    b2.seed(cfg.seed)
    b2.defaultclock.dt = cfg.sim.dt_ms * ms

    net_c, mix, mech = cfg.network, cfg.mixing, cfg.mechanisms
    tl = build_timeline(cfg)
    enc = tl.segment("encode")
    nm = build_nm(cfg, tl, inputs.env, inputs.env_rate)
    # explicit names: Brian2's default TimedArray names carry a process-global counter, so every run in
    # a reused build directory renamed them and forced a full recompile
    NM = b2.TimedArray(nm.nm, dt=NM_DT_S * second, name="ta_nm")
    scale = np.ones_like(nm.t)
    for seg in tl.segments:
        if seg.kind == "consolidate":
            scale[(nm.t >= seg.t0) & (nm.t < seg.t1)] = cfg.noise.consolidation_scale
    noise_scale = b2.TimedArray(scale, dt=NM_DT_S * second, name="ta_noise")

    onsets = enc.t0 + envelope_onsets(inputs.env.mean(axis=(0, 1)), inputs.env_rate,
                                      cfg.theta.onset_z, cfg.theta.onset_refractory_s)
    th_t, th, th_phase = build_theta(cfg, tl.total_s, onsets, cfg.seed)
    THETA = b2.TimedArray(th, dt=THETA_DT_S * second, name="ta_theta")

    # Explicit, distinct `order` for every object that draws random numbers. They all share one RNG stream,
    # and Brian2 breaks scheduling ties in a process-dependent order -- measured: the same seed gave one of
    # TWO spike trains depending on the process. Both are valid realisations; only one is reproducible.
    # MSO neurophonic as a field (volts) on the timeline clock, for the ephaptic term. r_field maps one
    # EPSC-unit of mean postsynaptic current to r_field_Mohm * 1 nA -- a mV-scale field, by construction.
    eph = cfg.ephaptic; NPH = None
    if eph.g_eph_nS > 0:
        dt_n = 2e-4; nph_v = np.zeros(int(np.ceil(tl.total_s / dt_n)) + 2)
        if eph.use_neurophonic and inputs.neurophonic is not None:
            def lay(n, t0):
                x = np.interp(np.arange(0, n.total.size / n.fs, dt_n), np.arange(n.total.size) / n.fs, n.total)
                k0 = int(round(t0 / dt_n)); m = min(x.size, nph_v.size - k0)
                nph_v[k0:k0 + m] += x[:m] * eph.r_field_Mohm * 1e6 * 1e-9          # EPSC units -> nA -> volts
            lay(inputs.neurophonic, enc.t0)
            for seg in tl.recalls():
                if seg.cue_s > 0 and inputs.neurophonic_cue is not None:
                    lay(inputs.neurophonic_cue, seg.t0)
        NPH = b2.TimedArray(nph_v * b2.volt, dt=dt_n * second, name="ta_nph")
    E = nmodel.make_group(net_c.n_exc, net_c.exc, cfg, "exc", NM, noise_scale, "exc", rng, THETA, order=0, nph=NPH)
    I = nmodel.make_group(net_c.n_inh, net_c.inh, cfg, "inh", NM, noise_scale, "inh", rng, THETA, order=1, nph=NPH)

    # ---- input layer: spike trains + metadata from whichever front end produced them ----
    si = inputs.spikes_enc
    ts, ids = [si.t + enc.t0], [si.i]
    for seg in tl.recalls():
        if seg.cue_s > 0 and inputs.spikes_cue is not None:
            c = inputs.spikes_cue.window(0.0, seg.cue_s)
            ts.append(c.t + seg.t0); ids.append(c.i)
    ts, ids = np.concatenate(ts), np.concatenate(ids)
    dt_s = cfg.sim.dt_ms * 1e-3
    key = np.unique(np.stack([ids, np.round(ts / dt_s).astype(np.int64)]), axis=1)   # one spike per unit per step
    order = np.argsort(key[1], kind="stable")
    IN = b2.SpikeGeneratorGroup(si.n, key[0][order], key[1][order] * dt_s * second, name="inp")
    # normalised input weight: every front end delivers the same mean conductance to an E cell
    k_in = max(mix.p_in_exc * si.n, 1e-9)
    w_in_nS = mix.g_in_mean_nS / (k_in * max(si.mean_rate(), 1e-9) * net_c.tau_e_ms * 1e-3)

    def rand_conn(n_pre, n_post, p, no_self=False):
        m = rng.random((n_pre, n_post)) < p
        if no_self:
            np.fill_diagonal(m, False)
        return np.nonzero(m)

    in_ns = dict(w_in=w_in_nS * nS, k_gain=cfg.neuromod.k_gain, nm_ref=cfg.neuromod.nm_ref, NM=NM)
    in_pre = "g_ext_post += w_in*clip(1 + k_gain*(NM(t) - nm_ref), 0, 5)"      # NM scales input gain
    S_in_e = b2.Synapses(IN, E, on_pre=in_pre, namespace=in_ns, name="in_e")
    i_, j_ = rand_conn(si.n, net_c.n_exc, mix.p_in_exc); S_in_e.connect(i=i_, j=j_)
    S_in_i = b2.Synapses(IN, I, on_pre=in_pre, namespace=in_ns, name="in_i")
    i_, j_ = rand_conn(si.n, net_c.n_inh, mix.p_in_inh); S_in_i.connect(i=i_, j=j_)

    # ---- plastic E->E: calcium early phase + tagging and capture ----
    ee_ns = stc.namespace(cfg)
    if cfg.eval.freeze_plasticity_at_recall:
        pl = np.ones_like(nm.t)
        for seg in tl.recalls():
            pl[(nm.t >= seg.t0) & (nm.t < seg.t1)] = 0.0
        ee_ns["pl_t"] = b2.TimedArray(pl, dt=NM_DT_S * second, name="ta_plt")
    S_ee = b2.Synapses(E, E, stc.plastic_model(cfg), on_pre=stc.ON_PRE, on_post=stc.ON_POST,
                       delay=stc.delays(cfg), method="heun", namespace=ee_ns,
                       dt=cfg.plasticity.update_dt_ms * ms, name="ee", order=2)
    ee_i, ee_j = rand_conn(net_c.n_exc, net_c.n_exc, net_c.p_conn, no_self=True)
    S_ee.connect(i=ee_i, j=ee_j)
    S_ee.h = 1.0
    S_ee.z = 0.0

    ax = net_c.axon_delay_ms * ms
    S_ei = b2.Synapses(E, I, on_pre="g_e_post += w_syn", namespace=dict(w_syn=net_c.w_ei_nS * nS), delay=ax, name="ei")
    i_, j_ = rand_conn(net_c.n_exc, net_c.n_inh, net_c.p_conn); S_ei.connect(i=i_, j=j_)
    S_ie = b2.Synapses(I, E, on_pre="g_i_post += w_syn; g_b_post += w_b",
                       namespace=dict(w_syn=net_c.w_ie_nS * nS, w_b=net_c.w_ie_b_nS * nS), delay=ax, name="ie")
    i_, j_ = rand_conn(net_c.n_inh, net_c.n_exc, net_c.p_conn); S_ie.connect(i=i_, j=j_)
    S_ii = b2.Synapses(I, I, on_pre="g_i_post += w_syn", namespace=dict(w_syn=net_c.w_ii_nS * nS), delay=ax, name="ii")
    i_, j_ = rand_conn(net_c.n_inh, net_c.n_inh, net_c.p_conn, no_self=True); S_ii.connect(i=i_, j=j_)

    # ---- gap junctions ----
    objs = [E, I, IN, S_in_e, S_in_i, S_ee, S_ei, S_ie, S_ii]
    gate_m = None
    if mech.mismatch_gate:
        # C2: pool the cells' own feedforward-vs-recurrent mismatch into one population value and hand it
        # back to every E cell. Computed entirely from synaptic currents inside the network.
        GATE = b2.NeuronGroup(1, "M_sum : 1", name="gate")
        S_g_in = b2.Synapses(E, GATE, "M_sum_post = mism_pre/n_e : 1 (summed)", namespace=dict(n_e=float(net_c.n_exc)), name="gate_in")
        S_g_in.connect()
        S_g_out = b2.Synapses(GATE, E, "M_pop_post = M_sum_pre : 1 (summed)", name="gate_out"); S_g_out.connect()
        gate_m = b2.StateMonitor(GATE, "M_sum", record=True, dt=10 * ms, name="gate_m")
        objs += [GATE, S_g_in, S_g_out, gate_m]
    gap_pairs = []
    if mech.gap_junctions:
        gap_pairs = gapmod.ring_pairs(net_c.n_inh, cfg.gap.neighbourhood, cfg.gap.p, rng)
        g = gapmod.conductance_for_cc(cfg.gap.coupling_coefficient, net_c.inh.gL_nS)
        objs.append(gapmod.make_gap(I, gap_pairs, g, cfg.gap.modulation, "gap_ii"))
        if cfg.gap.ee_enabled:   # weakly supported biologically; OFF by default
            pairs = [(a, c) for a in range(net_c.n_exc) for c in range(a + 1, net_c.n_exc)
                     if rng.random() < cfg.gap.ee_p]
            g_ee = gapmod.conductance_for_cc(cfg.gap.ee_coupling_coefficient, net_c.exc.gL_nS)
            objs.append(gapmod.make_gap(E, pairs, g_ee, cfg.gap.modulation, "gap_ee"))

    # Same reason, for spike propagation: two pathways adding into one variable (pre_ca and post both add
    # to Ca) round differently depending on which runs first, and a chaotic network amplifies 1e-16.
    k_order = 0
    for syn in [o for o in objs if isinstance(o, b2.Synapses)]:
        for pw in syn._pathways:
            pw.order = k_order; k_order += 1

    # ---- monitors ----
    # C5 provenance: each spike's OWN feedforward and recurrent excitatory current, recorded for analysis.
    # A monitor only reads; a test asserts the spike train is identical with it on and off.
    sm_e = b2.SpikeMonitor(E, variables=["g_ext", "g_e", "V"] if cfg.sim.log_provenance else None, name="sp_e")
    sm_i = b2.SpikeMonitor(I, name="sp_i")
    st_dt = cfg.sim.state_log_dt_ms * ms
    st_e = b2.StateMonitor(E, "nstate", record=True, dt=st_dt, name="st_e")
    st_i = b2.StateMonitor(I, "nstate", record=True, dt=st_dt, name="st_i")
    rw = cfg.decode.rank_window_ms * ms
    rank_m = b2.StateMonitor(E, "drive_acc", record=True, dt=rw, when="end", order=0, name="rank_m")
    rank_reset = E.run_regularly("drive_acc = 0*siemens", dt=rw, when="end", order=1, name="rank_reset")
    slow = b2.StateMonitor(E, ["p", "creb", "I_drift"], record=True, dt=cfg.sim.slow_log_dt_s * second, name="slow")
    n_syn = len(ee_i)
    logged = np.arange(n_syn) if n_syn <= 20000 else np.sort(rng.choice(n_syn, 5000, replace=False))
    w_m = b2.StateMonitor(S_ee, ["h", "z"], record=logged, dt=cfg.sim.weight_log_dt_s * second, name="w_m")
    # LFP/EEG proxy: population sums of synaptic current onto E cells, recorded at 1 ms
    LFP = b2.NeuronGroup(1, "Ie_sum : amp\nIi_sum : amp\nIr_sum : amp", name="lfp")
    S_lfp = b2.Synapses(E, LFP, "Ie_sum_post = I_exc_pre : amp (summed)\nIi_sum_post = I_inh_pre : amp (summed)\nIr_sum_post = I_rec_pre : amp (summed)",
                        namespace=dict(E_e=net_c.E_e_mV * mV, E_i=net_c.E_i_mV * mV, E_K=net_c.E_K_mV * mV), name="lfp_syn")
    S_lfp.connect()
    if eph.g_eph_nS > 0 and eph.use_lfp:
        # network field = r_field x MEAN NET synaptic current per E cell (excitatory inward +, inhibitory -),
        # fed back to every cell. One dt of lag; linear.
        fld_ns = dict(r_field=eph.r_field_Mohm * b2.Mohm, n_e=float(net_c.n_exc))
        for grp, nm_ in ((E, "fld_e"), (I, "fld_i")):
            Sf = b2.Synapses(LFP, grp, "V_field_post = r_field*(Ie_sum_pre + Ii_sum_pre)/n_e : volt (summed)", namespace=fld_ns, name=nm_)
            Sf.connect(); objs.append(Sf)
    lfp_m = b2.StateMonitor(LFP, ["Ie_sum", "Ii_sum", "Ir_sum"], record=True, dt=1 * ms, name="lfp_m")
    objs += [sm_e, sm_i, st_e, st_i, rank_m, rank_reset, slow, w_m, LFP, S_lfp, lfp_m]

    net = b2.Network(*objs)
    for seg in tl.segments:
        on = seg.kind in cfg.sim.log_states_in
        st_e.active = st_i.active = on
        net.run(seg.dur * second, profile=cfg.sim.profile)
    profile = ""
    if cfg.sim.device == "cpp_standalone":
        # No build lock. The thrash first blamed on "parallel builds" (267 s each against 20 s alone) was
        # the bare `-j`: six builds x ~100 clang each. With -j3 per build, six concurrent builds are 18
        # processes; a lock on top of that serialised ~30 s per job and capped throughput at 2 jobs/min.
        b2.device.build(directory=str(build_dir), compile=True, run=False, debug=False, clean=False)
        b2.device.run(str(build_dir), with_output=False, run_args=[])
    if cfg.sim.profile:
        try:
            profile = str(b2.profiling_summary(net, show=12))
        except Exception as e:                      # profiling is a convenience, never a failure
            profile = f"(profiling unavailable: {e})"

    res = RunResult(
        cfg=cfg, timeline=tl, nm=nm, n_exc=net_c.n_exc, n_inh=net_c.n_inh,
        spikes_e=(np.array(sm_e.i), np.array(sm_e.t / second)),
        spikes_i=(np.array(sm_i.i), np.array(sm_i.t / second)),
        state_t=np.array(st_e.t / second),
        state_e=np.array(st_e.nstate, dtype=np.int8), state_i=np.array(st_i.nstate, dtype=np.int8),
        rank_t=np.array(rank_m.t / second), drive=np.array(rank_m.drive_acc / nS),
        slow_t=np.array(slow.t / second), p=np.array(slow.p), creb=np.array(slow.creb),
        drift=np.array(slow.I_drift / pA),
        w_t=np.array(w_m.t / second), h_log=np.array(w_m.h), z_log=np.array(w_m.z),
        syn_i=ee_i, syn_j=ee_j, h_final=np.array(S_ee.h[:]), z_final=np.array(S_ee.z[:]),
        # state variables are recorded (a monitor cannot resolve the group's constants inside a subexpression);
        # the currents are formed here exactly as the model forms them: g * (E_e - V)
        spike_Iff=np.array(sm_e.g_ext * (net_c.E_e_mV * mV - sm_e.V) / pA) if cfg.sim.log_provenance else None,
        spike_Irec=np.array(sm_e.g_e * (net_c.E_e_mV * mV - sm_e.V) / pA) if cfg.sim.log_provenance else None,
        lfp_t=np.array(lfp_m.t / second), lfp_Ie=np.array(lfp_m.Ie_sum[0] / pA),
        lfp_Ii=np.array(lfp_m.Ii_sum[0] / pA), lfp_Ir=np.array(lfp_m.Ir_sum[0] / pA),
        theta_t=th_t, theta=th, theta_phase=th_phase, onsets_s=onsets,
        profile=profile,
        extra=dict(M_pop=(np.array(gate_m.t / second), np.array(gate_m.M_sum[0])) if gate_m is not None else None,
                   w_in_nS=float(w_in_nS), front_end=si.front_end, input_log=inputs.log,
                   n_gap_pairs=len(gap_pairs), n_ee=int(n_syn), logged_syn=logged),
    )
    res.wall_s = time.time() - t_wall
    return res
