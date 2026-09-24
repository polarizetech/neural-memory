"""Training, delays and probes for the minimal habituation model.

One run = one network (one seed) and one stimulus family. The network is trained on the stored sound;
snapshots are taken after the Nth presentation; each snapshot is carried through a delay (silence, or
other sounds then silence); then every probe is presented to its OWN copy of that network.

CONTROLS ARE TIME-MATCHED AND PAIRED. The comparison for every probe is the naive network carried through
exactly the same delay and interference, then given the IDENTICAL relay spike raster and the IDENTICAL
membrane-noise stream. So a suppression S = 1 - R_trained / R_control is due to the network's state and
nothing else -- not to a noisier draw, and not to the interference itself (which habituates channels too).

Long silences are FAST-FORWARDED: the depression pools and L obey linear ODEs under constant spontaneous
relay firing, so they are advanced in closed form (mean field), then the last `direct_silence_s` is
simulated directly so the probe meets a settled network. `tests/test_habituation.py` checks the
fast-forward against direct simulation.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import HabConfig
from .model import Net, Record, State, a_slow_spike, build_net, eta_pre, initial_state, run
from .periphery import Periphery, relay_spikes
from .stimuli import SoundSpec, silence


def _star(rec: float, lam: np.ndarray) -> np.ndarray:
    """Fixed point rec/lam of dL/dt = rec - lam L. Where lam == 0 (recovery frozen AND nothing eroding) L has no
    fixed point and does not move; any finite value works there because exp(-0 h) = 1 keeps L unchanged. Without
    this, 0/0 put NaN into L (found by the E01 smoke run; never reached with a finite recovery time)."""
    return np.divide(rec, lam, out=np.ones_like(lam, dtype=float), where=lam > 0)


@dataclass
class Sim:
    cfg: HabConfig
    per: Periphery
    net: Net
    post_spont: np.ndarray          # (NE,) mean postsynaptic trace in silence, for the fast-forward
    rate_e_spont: float             # Hz, measured

    @property
    def dt(self) -> float:
        return self.net.dt

    # ---------------------------------------------------------------- inputs
    def raster(self, spec: SoundSpec, rng: np.random.Generator, tail_s: float = 0.0) -> np.ndarray:
        r = self.per.relay_rate(spec)
        if tail_s > 0:
            r = np.vstack([r, self.per.relay_rate(silence(tail_s))])
        return relay_spikes(r, self.cfg.periphery.relay_per_cf, self.dt, rng)

    def present(self, st: State, spec: SoundSpec, rng: np.random.Generator) -> Record:
        return run(self.net, st, self.raster(spec, rng), rng)

    def quiet(self, st: State, seconds: float, rng: np.random.Generator) -> Record | None:
        if seconds <= 0:
            return None
        return run(self.net, st, self.raster(silence(seconds), rng), rng)

    # ---------------------------------------------------------------- delays
    def fast_forward(self, st: State, seconds: float, h: float = 5.0) -> None:
        """Mean-field advance through `seconds` of silence (spontaneous relay firing only)."""
        if seconds <= 0:
            return
        cfg = self.cfg
        d, lt, r0 = cfg.depression, cfg.longterm, cfg.periphery.relay_spont_hz
        U = d.U if d.on else 1.0
        n = max(int(np.ceil(seconds / h)), 1)
        h = seconds / n
        for _ in range(n):
            if d.on:
                lam_f = 1 / d.tau_fast_s + U * r0
                xf_star = (1 / d.tau_fast_s) / lam_f
                xf_mid = xf_star + (st.xf - xf_star) * np.exp(-lam_f * h / 2)
                st.xf = xf_star + (st.xf - xf_star) * np.exp(-lam_f * h)
                if d.slow_on:
                    lam_s = 1 / d.tau_slow_s + (a_slow_spike(cfg) * r0 if d.slow_per == "spike" else d.a_slow * r0 * U * xf_mid)
                    xs_star = (1 / d.tau_slow_s) / lam_s
                    xs_mid = xs_star + (st.xs - xs_star) * np.exp(-lam_s * h / 2)
                    st.xs = xs_star + (st.xs - xs_star) * np.exp(-lam_s * h)
                else:
                    xs_mid = st.xs
                R = r0 * U * xf_mid * xs_mid                     # release rate per relay unit
            else:
                R = np.full_like(st.xf, r0 * U)
            if lt.mode == "presynaptic":
                lam = 1 / lt.tau_s + eta_pre(cfg) * R
                Ls = _star(1 / lt.tau_s, lam)
                st.L = np.maximum(Ls + (st.L - Ls) * np.exp(-lam * h), lt.L_min)
            elif lt.mode == "hebbian":
                lam = 1 / lt.tau_s + lt.eta_hebb * R[:, :, None] * self.post_spont[None, None, :]
                Ls = _star(1 / lt.tau_s, lam)
                st.L = np.clip(Ls + (st.L - Ls) * np.exp(-lam * h), lt.L_min, lt.L_max)
        st.nm = st.nm * np.exp(-seconds / cfg.salience.tau_nm_s)
        st.ge[:] = 0; st.gi[:] = 0; st.gei[:] = 0
        st.post = np.repeat(self.post_spont[None, :], st.B, 0)
        st.t += seconds

    def advance(self, st: State, delay_s: float, rng: np.random.Generator,
                interference: list[SoundSpec] | None = None) -> None:
        """Carry `st` through a delay. With interference: those sounds, one every isi_s, fill the first
        interference_s; the rest is silence. The last direct_silence_s is always simulated directly."""
        p = self.cfg.protocol
        used = 0.0
        if interference:
            k = 0
            while used + p.isi_s <= min(p.interference_s, delay_s - p.direct_silence_s) + 1e-9:
                self.present(st, interference[k % len(interference)], rng)
                self.quiet(st, p.isi_s - p.stim_s, rng)
                used += p.isi_s
                k += 1
        rest = delay_s - used
        direct = min(p.direct_silence_s, rest)
        self.fast_forward(st, rest - direct)
        self.quiet(st, direct, rng)

    # ---------------------------------------------------------------- probes
    def probe(self, st: State, rasters: np.ndarray, noise_seed: int) -> Record:
        """Every raster (P, T, Nr) to its own copy of `st` (B must be 1). Same noise seed => paired."""
        s = st.tile(rasters.shape[0])
        return run(self.net, s, np.ascontiguousarray(rasters.transpose(1, 0, 2)), np.random.default_rng(noise_seed))


def make_sim(cfg: HabConfig, settle_s: float = 3.0) -> tuple[Sim, State]:
    """Build the network and return it with a naive state settled in silence."""
    per = Periphery(cfg)
    net = build_net(cfg, per.cf)
    st = initial_state(net)
    rng = np.random.default_rng(cfg.seed + 2)
    sim = Sim(cfg, per, net, np.zeros(net.n_exc), 0.0)
    rec = sim.quiet(st, settle_s, rng)
    sim.rate_e_spont = float(rec.e_count.sum() / (net.n_exc * settle_s))
    sim.post_spont = _effective_post(sim, st, rng)
    return sim, st


def _effective_post(sim: Sim, st: State, rng: np.random.Generator, seconds: float = 10.0) -> np.ndarray:
    """The postsynaptic factor the Hebbian fast-forward uses in silence, MEASURED by direct simulation.

    Mean field would use the mean trace, but a relay spike is what makes its target fire, so release and the
    postsynaptic trace are correlated and the product of means under-estimates erosion (by ~30 %, found by
    tests/test_habituation.py). So: a copy with L = 1 runs `seconds` of silence directly, and the per-cell
    factor is read off the erosion it actually suffered: dL = -eta R_spont p_eff dt  =>  p_eff = -dL/(eta R dt)."""
    from .model import spont_release
    cfg = sim.cfg
    if cfg.longterm.mode != "hebbian":
        return np.zeros(sim.net.n_exc)
    s = st.copy()
    s.L = np.ones_like(s.L)
    sim.quiet(s, seconds, rng)
    dL = 1.0 - s.L[0]                                                   # (Nr, NE); recovery over 10 s ~ 0.3 %
    w = sim.net.W0 > 0
    per_cell = (dL * w).sum(0) / np.maximum(w.sum(0), 1)
    return per_cell / (cfg.longterm.eta_hebb * spont_release(cfg) * seconds)


def calibrate_salience(sim: Sim, st: State, specs: list[SoundSpec]) -> None:
    """Set st.drive_ref and st.k_nm, with NM's EFFECTS held off (gain 0, no potentiation), on a naive network.

    drive_ref = mean peak salience drive to the NEUTRAL calibration sounds (the unit of salience.theta).
    k_nm      = the NM gain at which their LOUD (+salient_db) versions peak at salience.nm_target. With effects
                off NM is linear in the gain, so this is solved, not searched. Doing it per mode is what makes
                raw and network start equal: without it the network-driven NM began ~30x smaller than the raw one
                on the very first presentation, and "salience fades under network" would have been true by
                construction. The calibration sounds are never probed and never used as interference."""
    from dataclasses import replace
    from .stimuli import louder
    cfg = sim.cfg
    if cfg.salience.mode == "off":
        return
    cc = cfg.model_copy(deep=True)
    cc.salience.gain, cc.salience.eta_pot = 0.0, 0.0
    net_c = replace(sim.net, cfg=cc)
    sim_c = replace(sim, cfg=cc, net=net_c)

    def peaks(level_specs, drive_ref, k, what):
        out = []
        for j, spec in enumerate(level_specs):
            s = st.copy()
            s.drive_ref, s.k_nm = drive_ref, k
            rec = run(net_c, s, sim_c.raster(spec, np.random.default_rng(cfg.seed + 700 + j)), np.random.default_rng(cfg.seed + 800 + j))
            out.append(getattr(rec, what).max())
        return float(np.mean(out))

    st.drive_ref = peaks(specs, 1.0, 0.0, "drive")
    loud = [louder(s, cfg.protocol.salient_db, cfg.periphery.level_db_spl) for s in specs]
    m1 = peaks(loud, st.drive_ref, 1.0, "nm")
    if m1 <= 0:
        raise RuntimeError("salience calibration: loud calibration sounds never crossed theta; NM gain undefined")
    st.k_nm = cfg.salience.nm_target / m1
    st.nm[:] = 0.0
