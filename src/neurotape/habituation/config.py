"""Configuration for the MINIMAL habituation model (``neurotape.habituation``).

Deliberately separate from ``neurotape.config.Config``: nothing here inherits the full model's AdEx cell,
T-current, GABA_B conductance, tagging, protein pool, CREB, theta or gap junctions. Every number is listed
with its source in ASSUMPTIONS.md, section "Minimal habituation model". Unknown keys raise, as in the
full model, because a typo in an arm would otherwise silently run another arm.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Periphery(_Strict):
    # "an"   = Zilany, Bruce & Carney 2014 through `cochlea` -> pooled per-CF rate -> relay (PRIMARY)
    # "rate" = gammatone envelope -> sigmoid rate-level function -> relay (labelled rate model; no cochlea)
    kind: Literal["an", "rate"] = "an"
    n_cf: int = Field(32, ge=4)
    f_lo_hz: float = 125.0                  # zilany2014 human lower limit
    f_hi_hz: float = 7000.0
    anf_per_cf: list[int] = [6, 2, 2]       # HSR, MSR, LSR fibres pooled per CF ("an" only)
    level_db_spl: float = 60.0              # neutral presentation level
    relay_per_cf: int = Field(8, ge=1)      # relay (thalamic-like) units per CF
    relay_spont_hz: float = 1.0             # relay spontaneous rate (MGB-like: low, unlike HSR AN fibres)
    relay_max_hz: float = 150.0
    an_driven_ref_hz: float = 250.0         # pooled-AN driven rate (above spontaneous) mapped to relay_max_hz
    rate_threshold_db: float = 20.0         # "rate" kind: band level at the sigmoid midpoint minus half range
    rate_dynamic_range_db: float = 40.0
    smooth_ms: float = 5.0                  # rate smoothing before Poisson relay spikes


class Depression(_Strict):
    """Short-term depression of relay->E synapses, two timescales (Tsodyks & Markram 1997 one-pool model;
    a second, slower pool for the "tens of seconds" component of SSA, Ulanovsky et al. 2004)."""
    on: bool = True
    U: float = Field(0.5, gt=0, le=1)       # fraction of the fast pool released per spike
    tau_fast_s: float = 0.8                 # recovery of the fast pool (~1 s, Tsodyks & Markram 1997)
    slow_on: bool = True
    a_slow: float = Field(0.05, ge=0, le=1)  # slow-pool depletion per unit RELEASE (not per spike)
    tau_slow_s: float = 20.0                # "tens of seconds" (Ulanovsky et al. 2004)
    # What depletes the slow pool. "release" (preregistered): a_slow per unit release -- but release saturates at
    # ~1/tau_fast once a channel fires above a few Hz, so the slow trace records WHETHER a channel was active, not
    # how strongly (found by the first hab_memory run). "spike" (EXPLORATORY, post hoc): a fixed fraction per
    # presynaptic spike, rate-graded; its fraction is DERIVED so the spontaneous steady state equals "release"'s.
    slow_per: Literal["release", "spike"] = "release"


class LongTerm(_Strict):
    """Long-term change of relay->E efficacy, a multiplicative factor L (1 = naive). Placeholders."""
    # off         : no long-term change (step 1)
    # presynaptic : L per relay fibre, depleted by that fibre's own release, whatever the target does
    #               (homosynaptic, Aplysia-like). Spontaneous release also depletes it.
    # hebbian     : L per synapse, depleted by release x postsynaptic activity (anti-Hebbian depression):
    #               only synapses that drive a responding cell weaken.
    mode: Literal["off", "presynaptic", "hebbian"] = "off"
    # eta_pre is DERIVED, not chosen: the value at which spontaneous release alone holds L at pre_spont_L
    # (the mechanism is engaged by silence; see model.eta_pre). An absolute eta would mean nothing.
    pre_spont_L: float = Field(0.8, gt=0, lt=1)
    eta_hebb: float = 0.05                  # engagement criterion: 16 presentations -> L on the stored channels ~0.87
    tau_s: float = 3600.0                   # recovery of L toward 1
    L_min: float = 0.05
    L_max: float = 2.0                      # ceiling for NM-gated potentiation (step 3)
    post_tau_ms: float = 100.0              # postsynaptic activity trace


class FFInh(_Strict):
    """Feedforward inhibition: relay -> FF (tonotopic LIF inhibitory cells) -> E. model-v0.2.0, E02.

    The FF->E conductance is W_fe * G, with G a per-synapse multiplier starting at g0 (NON-ZERO: removing a pathway
    that starts at zero is not a manipulation). With `plastic`, G follows the inhibitory STDP rule of Vogels et al.
    2011 (Science 10.1126/science.1211095; equation from background knowledge, abstract read): on an FF spike,
    G += eta (x_post - alpha); on an E spike, G += eta x_pre; traces decay with tau_stdp and step by 1 per spike;
    alpha = 2 rho0 tau_stdp, rho0 = the network's MEASURED spontaneous E rate (set by make_sim). At the default
    operating point FF cells are silent at rest, so silence cannot move G except by its relaxation toward g0 (which
    is what the fast-forward does). Synapses whose E cell fires above rho0 while their FF cell is active
    potentiate: a learned, stimulus-specific negative image. G relaxes to g0 with tau_s. Off by default."""
    on: bool = False
    n_ff: int = Field(50, ge=2)
    tonotopic_sigma_oct: float = 0.3
    w_rf_nS: float = 0.6                    # relay->FF peak conductance (no short-term depression on this path)
    w_fe_nS: float = 0.3                    # FF->E peak conductance at G = 1
    g0: float = Field(1.0, gt=0)            # initial (and resting) multiplier
    plastic: bool = False
    eta: float = 0.0
    tau_stdp_ms: float = 20.0               # Vogels et al. 2011 [BG]
    tau_s: float = 3600.0                   # relaxation of G toward g0 (matched to longterm.tau_s)
    G_max: float = 20.0


class Receptor(_Strict):
    """Postsynaptic receptor inactivation on relay->E synapses (Rajan & Marshall 2025, Curr Biol
    10.1016/j.cub.2025.05.071, [FT]). model-v0.2.0, E02.

    Per relay fibre (every synapse of a fibre sees the same release, so per-synapse pools would be identical):
    surface S (the efficacy multiplier) and internalised I. On release `rel`: k_int*rel*S moves S -> I. Between:
        dS/dt = k_syn - k_deg S + k_rec I          dI/dt = -(k_rec + k_deg + k_des) I
    (their eq. 2 prints -(k_rec - k_deg + k_des); the text says both pools degrade at k_deg, so +k_deg is used).
    Rates are theirs, read PER MINUTE (stimuli were one per minute; the paper gives no unit) and converted to /s.
    k_syn is DERIVED so the naive network under spontaneous release sits at S = 1. `synthesis_scale` multiplies
    k_syn (the synthesis block). Off by default."""
    on: bool = False
    k_int: float = Field(2e-4, ge=0)        # fraction of surface receptors internalised per unit release [ARBITRARY]
    k_rec_per_min: float = 0.1
    k_deg_per_min: float = 0.02
    k_des_per_min: float = 0.005
    synthesis_scale: float = Field(1.0, ge=0)


class Salience(_Strict):
    """A global LC-like signal NM(t). Step 3."""
    # off     : NM = 0
    # raw     : driven by the UNADAPTED relay input (spike counts). Cannot habituate across presentations.
    # network : driven by the E population's own response, which carries the depression. If salience
    #           fades with repetition here and not under "raw", that fading is habituation showing itself.
    mode: Literal["off", "raw", "network"] = "off"
    tau_fast_ms: float = 20.0
    tau_slow_s: float = 1.0                 # drive = [fast - slow]_+ : an onset / change detector
    theta: float = 0.5                      # drive threshold, in units of the naive NEUTRAL onset drive (drive_ref)
    # The NM gain is not a free number: it is SOLVED per run and per mode so that loud (+salient_db) calibration
    # sounds give this NM peak in a naive network. Both modes then start equal; only repetition can separate them.
    nm_target: float = 1.0
    tau_nm_s: float = 0.5
    # effects of NM
    gain: float = 1.0                       # input gain = 1 + gain*NM (sensitisation / dishabituation)
    eta_pot: float = 0.0                    # NM-gated potentiation of L: eta_pot*NM*release*post*(L_max-L)
                                            # (step-3 value 0.10 = 2 x eta_hebb: at NM = 1 a synapse at L = 1 is
                                            # potentiated as strongly as a neutral one is depressed)


class Network(_Strict):
    n_exc: int = Field(200, ge=4)
    n_inh: int = Field(50, ge=2)
    dt_ms: float = 0.5
    C_e_pF: float = 200.0
    C_i_pF: float = 100.0
    gL_nS: float = 10.0
    EL_mV: float = -70.0
    VT_mV: float = -50.0
    Vr_mV: float = -60.0
    t_ref_ms: float = 2.0
    E_e_mV: float = 0.0
    E_i_mV: float = -80.0
    tau_e_ms: float = 5.0
    tau_i_ms: float = 10.0
    noise_mV: float = 3.0                   # SD of the membrane noise (white, integrated over tau_m)
    I0_pA: float = 80.0                     # constant background current (operating-point scan, ASSUMPTIONS.md)
    tonotopic_sigma_oct: float = 0.3
    w_in_nS: float = 8.0                    # relay->E peak conductance at full efficacy (operating-point scan)
    p_ei: float = 0.2
    w_ei_nS: float = 2.0
    p_ie: float = 0.3
    w_ie_nS: float = 4.0


class Protocol(_Strict):
    stim_s: float = 1.5
    isi_s: float = 3.0                      # onset-to-onset
    n_reps: list[int] = [1, 2, 4, 8, 16]    # checkpoints along ONE training sequence
    delays_s: list[float] = [2.0, 30.0, 300.0, 1800.0]
    interference_s: float = 20.0            # other sounds right after training ("life goes on")
    interference_min_delay_s: float = 30.0  # interference arm only where the delay can hold it
    n_novel: int = Field(20, ge=5)          # the foreign-stimulus null
    shifts_oct: list[float] = [1 / 6, 1 / 2]
    probe_tail_s: float = 0.3
    direct_silence_s: float = 2.0           # silence simulated directly before fast-forwarding the rest
    salient_db: float = 15.0                # step 3: the salient version is this much louder


class HabConfig(_Strict):
    seed: int = 0
    periphery: Periphery = Periphery()
    depression: Depression = Depression()
    longterm: LongTerm = LongTerm()
    ffinh: FFInh = FFInh()
    receptor: Receptor = Receptor()
    salience: Salience = Salience()
    network: Network = Network()
    protocol: Protocol = Protocol()

    @model_validator(mode="after")
    def _deps(self):
        if self.salience.eta_pot > 0 and self.longterm.mode != "hebbian":
            raise ValueError("salience.eta_pot writes the per-synapse L: it needs longterm.mode: hebbian")
        if self.ffinh.plastic and not self.ffinh.on:
            raise ValueError("ffinh.plastic needs ffinh.on")
        if self.ffinh.plastic and self.ffinh.eta <= 0:
            raise ValueError("ffinh.plastic with eta <= 0 would never learn")
        if self.salience.mode == "off" and (self.salience.eta_pot > 0):
            raise ValueError("salience.eta_pot > 0 with salience.mode off would never act")
        return self


def load(path: str | Path | None) -> HabConfig:
    if path is None:
        return HabConfig()
    return HabConfig.model_validate(yaml.safe_load(Path(path).read_text()) or {})


def dump(cfg: HabConfig, path: str | Path) -> None:
    Path(path).write_text(yaml.safe_dump(cfg.model_dump(), sort_keys=False))
