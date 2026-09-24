"""The minimal habituation network: relay -> (depressing synapses) -> tonotopic LIF E cells <-> I cells.

What is IN it, and nothing else:
  * relay units, n_cf x relay_per_cf, Poisson from the periphery's per-CF rate
  * relay->E synapses with two-timescale short-term depression (fast pool x slow pool), tonotopic weights
  * an optional long-term efficacy factor L (presynaptic or anti-Hebbian depression; NM-gated potentiation)
  * conductance-based LIF E and I cells, E->I->E lateral inhibition, white membrane noise
  * an optional global LC-like signal NM(t) with two effects: input gain, and gating of potentiation

What is deliberately NOT in it: E->E recurrence, AdEx adaptation, T-current, GABA_B, tagging and capture,
protein pools, CREB, theta, gap junctions. It shares no neuron code with the full model.

The simulator is plain numpy, time-stepped (default 0.5 ms), and BATCHED: state arrays carry a leading
batch axis so a set of probes can be presented to identical copies of one network at once. Presenting each
probe to its own copy is the numerical form of testing separate animals: the probe cannot habituate the
network the next probe sees.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

import numpy as np

from .config import HabConfig


# ------------------------------------------------------------------ static structure
@dataclass
class Net:
    cfg: HabConfig
    cf_relay: np.ndarray            # (Nr,) CF of each relay unit
    cf_e: np.ndarray                # (NE,) preferred CF of each E cell
    W0: np.ndarray                  # (Nr, NE) relay->E peak conductance (nS), tonotopic
    W_ei: np.ndarray                # (NE, NI) nS
    W_ie: np.ndarray                # (NI, NE) nS
    dt: float

    @property
    def n_relay(self) -> int:
        return self.W0.shape[0]

    @property
    def n_exc(self) -> int:
        return self.W0.shape[1]


def build_net(cfg: HabConfig, cf: np.ndarray) -> Net:
    n, p = cfg.network, cfg.periphery
    rng = np.random.default_rng(cfg.seed + 1)
    cf_relay = np.repeat(cf, p.relay_per_cf)
    cf_e = np.geomspace(cf[0], cf[-1], n.n_exc) * 2 ** rng.uniform(-0.05, 0.05, n.n_exc)
    d_oct = np.log2(cf_relay[:, None] / cf_e[None, :])
    W0 = n.w_in_nS * np.exp(-0.5 * (d_oct / n.tonotopic_sigma_oct) ** 2)
    W0[W0 < 0.05 * n.w_in_nS] = 0.0
    W0 *= rng.uniform(0.7, 1.3, W0.shape) * (rng.random(W0.shape) < 0.8)
    W_ei = n.w_ei_nS * (rng.random((n.n_exc, n.n_inh)) < n.p_ei)
    W_ie = n.w_ie_nS * (rng.random((n.n_inh, n.n_exc)) < n.p_ie)
    return Net(cfg, cf_relay, cf_e, W0, W_ei.astype(float), W_ie.astype(float), n.dt_ms * 1e-3)


# ------------------------------------------------------------------ dynamic state
@dataclass
class State:
    V: np.ndarray                   # (B, NE) volts
    ge: np.ndarray                  # (B, NE) nS
    gi: np.ndarray
    ref: np.ndarray                 # (B, NE) steps of refractoriness left
    Vi: np.ndarray                  # (B, NI)
    gei: np.ndarray                 # (B, NI) excitation onto I
    refi: np.ndarray
    post: np.ndarray                # (B, NE) postsynaptic activity trace
    xf: np.ndarray                  # (B, Nr) fast pool
    xs: np.ndarray                  # (B, Nr) slow pool
    L: np.ndarray | None            # (B, Nr) presynaptic | (B, Nr, NE) hebbian | None
    nm: np.ndarray                  # (B,)
    s_fast: np.ndarray              # (B,) salience low-passes
    s_slow: np.ndarray
    t: float = 0.0
    drive_ref: float = 1.0          # naive neutral onset drive, for salience units (set by calibration)
    k_nm: float = 0.0               # NM gain; 0 = inert until calibrate_salience solves it (loud sounds -> nm_target)
    log: dict = field(default_factory=dict)

    @property
    def B(self) -> int:
        return self.V.shape[0]

    def copy(self) -> "State":
        return copy.deepcopy(self)

    def tile(self, B: int) -> "State":
        """B identical copies of a single-network state."""
        if self.B != 1:
            raise ValueError("tile() expects a single network (B == 1)")
        s = self.copy()
        for k, v in vars(s).items():
            if isinstance(v, np.ndarray) and v.ndim >= 1 and v.shape[0] == 1:
                setattr(s, k, np.repeat(v, B, axis=0))
        return s


def steady_pools(cfg: HabConfig) -> tuple[float, float]:
    """Fast and slow pool at steady state under spontaneous relay firing (mean field)."""
    d, r0 = cfg.depression, cfg.periphery.relay_spont_hz
    if not d.on:
        return 1.0, 1.0
    xf = 1.0 / (1.0 + d.U * r0 * d.tau_fast_s)
    xs = 1.0 / (1.0 + d.a_slow * r0 * d.U * xf * d.tau_slow_s) if d.slow_on else 1.0   # identical for both slow_per
    return xf, xs


def a_slow_spike(cfg: HabConfig) -> float:
    """slow_per = "spike": the per-spike fraction giving the SAME spontaneous steady state as per-release depletion
    (xs* = 1/(1 + a r0 tau_s)), i.e. a = a_slow * U * xf*. Derived, never chosen."""
    d, r0 = cfg.depression, cfg.periphery.relay_spont_hz
    xf = 1.0 / (1.0 + d.U * r0 * d.tau_fast_s)
    return d.a_slow * d.U * xf


def spont_release(cfg: HabConfig) -> float:
    """Mean release rate per relay synapse in silence (mean field)."""
    xf, xs = steady_pools(cfg)
    return cfg.periphery.relay_spont_hz * (cfg.depression.U if cfg.depression.on else 1.0) * xf * xs


def eta_pre(cfg: HabConfig) -> float:
    """Presynaptic long-term rate at which spontaneous release alone holds L at pre_spont_L:
    L* = 1 / (1 + eta R tau)  =>  eta = (1/L* - 1) / (R tau)."""
    lt = cfg.longterm
    return (1.0 / lt.pre_spont_L - 1.0) / (spont_release(cfg) * lt.tau_s)


def initial_state(net: Net) -> State:
    cfg = net.cfg
    n, lt = cfg.network, cfg.longterm
    NE, NI, Nr = n.n_exc, n.n_inh, net.n_relay
    xf, xs = steady_pools(cfg)
    if lt.mode == "presynaptic":
        L = np.full((1, Nr), lt.pre_spont_L)
    elif lt.mode == "hebbian":
        L = np.ones((1, Nr, NE))
    else:
        L = None
    z = lambda k: np.zeros((1, k))
    return State(V=np.full((1, NE), n.EL_mV * 1e-3), ge=z(NE), gi=z(NE), ref=z(NE), Vi=np.full((1, NI), n.EL_mV * 1e-3),
                 gei=z(NI), refi=z(NI), post=z(NE), xf=np.full((1, Nr), xf), xs=np.full((1, Nr), xs), L=L,
                 nm=np.zeros(1), s_fast=np.zeros(1), s_slow=np.zeros(1))


# ------------------------------------------------------------------ simulation
@dataclass
class Record:
    e_count: np.ndarray             # (T, B) E spikes per step
    cell_count: np.ndarray          # (B, NE) spikes per cell over the run
    nm: np.ndarray                  # (T, B)
    drive: np.ndarray               # (T, B) salience drive (units of drive_ref)


def run(net: Net, st: State, relay: np.ndarray, rng: np.random.Generator) -> Record:
    """Advance ``st`` in place over ``relay``: boolean spikes (T, B, Nr), or (T, Nr) shared by all B.

    Nothing here reads a stimulus label: the network sees relay spikes only."""
    cfg = net.cfg
    n, d, lt, sal = cfg.network, cfg.depression, cfg.longterm, cfg.salience
    dt = net.dt
    T = relay.shape[0]
    B = st.B
    shared = relay.ndim == 2
    NE, Nr = net.n_exc, net.n_relay
    C_e, C_i, gL = n.C_e_pF * 1e-12, n.C_i_pF * 1e-12, n.gL_nS * 1e-9
    EL, VT, Vr, Ee, Ei = (x * 1e-3 for x in (n.EL_mV, n.VT_mV, n.Vr_mV, n.E_e_mV, n.E_i_mV))
    I0 = n.I0_pA * 1e-12
    tau_m = n.C_e_pF / n.gL_nS * 1e-3
    tau_mi = n.C_i_pF / n.gL_nS * 1e-3
    sig_e = n.noise_mV * 1e-3 * np.sqrt(2 * dt / tau_m)
    sig_i = n.noise_mV * 1e-3 * np.sqrt(2 * dt / tau_mi)
    dec_e, dec_i = np.exp(-dt / (n.tau_e_ms * 1e-3)), np.exp(-dt / (n.tau_i_ms * 1e-3))
    dec_post = np.exp(-dt / (lt.post_tau_ms * 1e-3))
    rec_f = 1 - np.exp(-dt / d.tau_fast_s)
    rec_s = 1 - np.exp(-dt / d.tau_slow_s)
    a_f, a_s = dt / (sal.tau_fast_ms * 1e-3), dt / sal.tau_slow_s
    a_nm = dt / sal.tau_nm_s
    n_ref = int(round(n.t_ref_ms * 1e-3 / dt))
    U = d.U
    W0, W_ei, W_ie = net.W0, net.W_ei, net.W_ie
    L3 = lt.mode == "hebbian"
    L2 = lt.mode == "presynaptic"
    pot = sal.eta_pot > 0 and sal.mode != "off"
    e_pre = eta_pre(cfg) if L2 else 0.0
    per_spike = d.slow_per == "spike"
    a_sp = a_slow_spike(cfg)

    rec_e = np.zeros((T, B), np.int32)
    rec_nm = np.zeros((T, B))
    rec_drive = np.zeros((T, B))
    cells = np.zeros((B, NE), np.int32)
    V, ge, gi, ref, Vi, gei, refi, post = st.V, st.ge, st.gi, st.ref, st.Vi, st.gei, st.refi, st.post
    xf, xs, L, nm = st.xf, st.xs, st.L, st.nm

    n_block = int(round(1.0 / dt))
    fL = np.exp(-1.0 / lt.tau_s)
    for k in range(T):
        spk = relay[k][None, :].repeat(B, 0) if shared else relay[k]
        bi, fi = np.nonzero(spk)
        gain = 1.0 + sal.gain * nm if sal.mode != "off" else np.ones(B)
        if bi.size:
            if d.on:
                rel = U * xf[bi, fi] * (xs[bi, fi] if d.slow_on else 1.0)
            else:
                rel = np.full(bi.size, U)
            eff = W0[fi]
            if L3:
                eff = eff * L[bi, fi]
            elif L2:
                eff = eff * L[bi, fi][:, None]
            np.add.at(ge, bi, (rel * gain[bi])[:, None] * eff)
            if d.on:
                xf[bi, fi] -= U * xf[bi, fi]
                if d.slow_on:
                    if per_spike:
                        xs[bi, fi] -= a_sp * xs[bi, fi]
                    else:
                        xs[bi, fi] -= d.a_slow * rel
            if L2:
                L[bi, fi] = np.maximum(L[bi, fi] * (1 - e_pre * rel), lt.L_min)
            elif L3:
                Lk = L[bi, fi]
                pk = post[bi]
                Lk = Lk - lt.eta_hebb * rel[:, None] * pk * Lk
                if pot:
                    Lk = Lk + sal.eta_pot * (nm[bi] * rel)[:, None] * pk * (lt.L_max - Lk)
                L[bi, fi] = np.clip(Lk, lt.L_min, lt.L_max)
        # E cells
        active = ref <= 0
        dV = (gL * (EL - V) + ge * 1e-9 * (Ee - V) + gi * 1e-9 * (Ei - V) + I0) * (dt / C_e)
        V = np.where(active, V + dV + sig_e * rng.standard_normal(V.shape), Vr)
        ref = ref - 1
        se = V >= VT
        V = np.where(se, Vr, V)
        ref = np.where(se, n_ref, ref)
        # I cells
        activei = refi <= 0
        dVi = (gL * (EL - Vi) + gei * 1e-9 * (Ee - Vi) + I0 * 0.5) * (dt / C_i)
        Vi = np.where(activei, Vi + dVi + sig_i * rng.standard_normal(Vi.shape), Vr)
        refi = refi - 1
        si = Vi >= VT
        Vi = np.where(si, Vr, Vi)
        refi = np.where(si, n_ref, refi)
        # synapses
        ge = ge * dec_e
        gi = gi * dec_i
        gei = gei * dec_e
        sef = se.astype(float)
        if se.any():
            gei = gei + sef @ W_ei
        if si.any():
            gi = gi + si.astype(float) @ W_ie
        post = post * dec_post + sef
        # pools recover
        if d.on:
            xf += (1 - xf) * rec_f
            if d.slow_on:
                xs += (1 - xs) * rec_s
        # salience
        if sal.mode != "off":
            s = (spk.sum(1) / (Nr * dt)) if sal.mode == "raw" else (se.sum(1) / (NE * dt))
            st.s_fast = st.s_fast + a_f * (s - st.s_fast)
            st.s_slow = st.s_slow + a_s * (s - st.s_slow)
            drv = np.maximum(st.s_fast - st.s_slow, 0.0) / st.drive_ref
            nm = nm + a_nm * (-nm + st.k_nm * np.maximum(drv - sal.theta, 0.0))
            rec_drive[k] = drv
        rec_e[k] = se.sum(1)
        rec_nm[k] = nm
        cells += se
        if L is not None and (k + 1) % n_block == 0:      # hours-scale recovery, exact, once per simulated second
            L = 1.0 + (L - 1.0) * fL
    st.V, st.ge, st.gi, st.ref, st.Vi, st.gei, st.refi, st.post = V, ge, gi, ref, Vi, gei, refi, post
    st.nm, st.L = nm, L
    st.t += T * dt
    if L is not None and T % n_block:                       # the partial last second
        st.L = 1.0 + (st.L - 1.0) * np.exp(-(T % n_block) * dt / lt.tau_s)
    return Record(rec_e, cells, rec_nm, rec_drive)

