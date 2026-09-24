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
    salience: Salience = Salience()
    network: Network = Network()
    protocol: Protocol = Protocol()

    @model_validator(mode="after")
    def _deps(self):
        if self.salience.eta_pot > 0 and self.longterm.mode != "hebbian":
            raise ValueError("salience.eta_pot writes the per-synapse L: it needs longterm.mode: hebbian")
        if self.salience.mode == "off" and (self.salience.eta_pot > 0):
            raise ValueError("salience.eta_pot > 0 with salience.mode off would never act")
        return self


def load(path: str | Path | None) -> HabConfig:
    if path is None:
        return HabConfig()
    return HabConfig.model_validate(yaml.safe_load(Path(path).read_text()) or {})


def dump(cfg: HabConfig, path: str | Path) -> None:
    Path(path).write_text(yaml.safe_dump(cfg.model_dump(), sort_keys=False))
