"""YAML configuration, validated with pydantic.

Every mechanism in the network has a switch in ``Mechanisms``. An ablation is a config with one
switch flipped and nothing else changed -- see ``experiments/ablations.py``. Parameter sources are
listed in ASSUMPTIONS.md; the defaults here are the values that file documents.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Strict(BaseModel):
    # An unknown key is a typo, and a typo in an ablation config silently runs the full model.
    model_config = ConfigDict(extra="forbid")


class Frontend(_Strict):
    # "an" = auditory nerve (Zilany et al. 2014 via `cochlea`), the PRIMARY audio front end.
    # "filterbank" = envelope bands -> random projection -> Poisson: the ABLATION, and the only
    # route for non-audio CSV sensor streams.
    kind: Literal["an", "filterbank"] = "an"
    level_db_spl: float = 60.0              # per stream, before acoustic mixing (an only)
    anf_per_cf: list[int] = [6, 2, 2]       # HSR, MSR, LSR fibres per CF, kept as separate populations
    moc_enabled: bool = False               # efferent MOC-like feedback: tonic NM lowers cochlear gain
    moc_db_per_nm: float = 50.0
    brainstem: Literal["none", "cnmodel"] = "none"
    stereo: bool = False                    # two cochleae; mono input = identical L/R (ITD 0, ILD 0)
    azimuths_deg: list[float] = [-45.0, 45.0, 0.0, -90.0, 90.0]   # per stream index; ignored for stereo FILES
    spatial_ild_max_db: float = 20.0
    spatial_ild_corner_hz: float = 1500.0
    mso: bool = False                       # MSO coincidence population + neurophonic; needs stereo: true
    filterbank: Literal["gammatone", "logbp"] = "gammatone"
    n_bands: int = Field(32, ge=1)
    f_lo_hz: float = Field(80.0, gt=0)      # configurable down to 0.1 Hz for sensor data (use logbp)
    f_hi_hz: float = Field(8000.0, gt=0)
    envelope_rate_hz: float = 1000.0
    compression: float = Field(0.3, gt=0, le=1)  # power-law envelope compression
    csv_rate_hz: float | None = None        # used when a CSV has no time column
    max_seconds: float | None = None        # truncate streams (None = use encode_s)

    @model_validator(mode="after")
    def _check(self):
        if self.f_hi_hz <= self.f_lo_hz:
            raise ValueError("f_hi_hz must exceed f_lo_hz")
        if self.filterbank == "gammatone" and self.f_lo_hz < 20:
            raise ValueError("gammatone below 20 Hz is not meaningful; use filterbank: logbp")
        return self


class Mixing(_Strict):
    n_input: int = Field(64, ge=1)
    bands_per_input: int = Field(6, ge=1)   # sparse projection: bands drawn from ALL streams
    mode: Literal["mixed", "labelled"] = "mixed"
    label_purity: float = Field(0.8, ge=0, le=1)  # labelled debug mode only
    rate_max_hz: float = 80.0               # Poisson rate of an input neuron at drive = 1
    p_in_exc: float = 0.1
    p_in_inh: float = 0.1
    # The input weight is NORMALISED so every front end delivers the same mean input conductance
    # to an E cell: w_in = g_in_mean / (K_in * measured mean unit rate * tau_e). Without this an
    # AN front end (320 fibres at ~60 Hz) and the Poisson ablation are not comparable.
    g_in_mean_nS: float = 8.0


class NeuronParams(_Strict):
    C_pF: float = 200.0
    gL_nS: float = 10.0
    EL_mV: float = -70.0
    VT_mV: float = -50.0
    DeltaT_mV: float = 2.0
    V_cut_mV: float = -40.0
    V_reset_mV: float = -58.0
    t_ref_ms: float = 2.0
    a_nS: float = 2.0
    b_pA: float = 40.0
    tau_w_ms: float = 150.0
    gT_nS: float = 100.0                    # T-type Ca conductance; set ONLY by the single-cell tests
    E_Ca_mV: float = 120.0
    T_shift_mV: float = 2.0
    T_celsius: float = 36.0
    hT_loaded: float = 0.4                  # LOADED: T inactivation gate above this (burst onset in the step test)
    t_spike_ms: float = 1.0                 # SPIKE state window after threshold crossing
    t_reset_ms: float = 10.0                # RESET state = refractory + AHP window


class Network(_Strict):
    n_exc: int = Field(200, ge=2)
    n_inh: int = Field(50, ge=2)
    p_conn: float = 0.1                     # Luboeinski & Tetzlaff 2021, p_c
    g0_nS: float = 1.0                      # conductance equivalent of h_0
    w_ei_nS: float = 2.0
    w_ie_nS: float = 8.0
    w_ii_nS: float = 8.0
    tau_e_ms: float = 5.0                   # tau_syn in the reference
    tau_i_ms: float = 5.0
    E_e_mV: float = 0.0
    E_i_mV: float = -80.0
    # Slow GABA_B-like K+ conductance on I->E synapses. Without it inhibition reverses at -80 mV,
    # hT_inf(-78 mV) = 0.32, and the LOADED state (hT > 0.4) is unreachable by synaptic inhibition.
    E_K_mV: float = -95.0
    tau_b_ms: float = 150.0
    w_ie_b_nS: float = 1.0
    axon_delay_ms: float = 3.0              # t_ax_delay in the reference
    exc: NeuronParams = NeuronParams()
    inh: NeuronParams = NeuronParams(a_nS=0.0, b_pA=0.0, gT_nS=0.0, tau_w_ms=50.0,
                                     V_reset_mV=-60.0, C_pF=100.0)


class Noise(_Strict):
    I0_pA: float = 100.0                    # mean background current
    sigma_pA: float = 60.0                  # stationary SD of the fast OU background
    tau_ms: float = 5.0                     # tau_OU in the reference
    consolidation_scale: float = 1.0


class Drift(_Strict):
    tau_s: float = 10.0                     # slow OU drift of the tonic operating point
    sigma_pA: float = 20.0


class GapJunctions(_Strict):
    p: float = 0.3
    neighbourhood: int = 8                  # ring distance within which I cells may couple
    coupling_coefficient: float = Field(0.1, ge=0.0, lt=0.5)
    modulation: float = Field(1.0, ge=0.0)  # pH/Mg-like scalar on the conductance
    ee_enabled: bool = False                # weakly supported biologically; OFF by default
    ee_p: float = 0.02
    ee_coupling_coefficient: float = 0.02


class Plasticity(_Strict):
    # Dimensionless: everything is in units of h_0, keeping the published ratios.
    # Luboeinski & Tetzlaff 2021 (Commun Biol 4:275), Table of parameters; values as in
    # jlubo/brian_network_plasticity config_defaultnet.json.
    Ca_pre: float = 0.6
    Ca_post: float = 0.1655
    tau_Ca_ms: float = 48.8
    t_Ca_delay_ms: float = 18.8
    theta_p: float = 3.0
    theta_d: float = 1.2
    gamma_p: float = 1645.6
    gamma_d: float = 313.1
    tau_h_s: float = 688.4
    h_max: float = 2.3805                   # 10 mV / 4.20075 mV
    sigma_pl: float = 0.6914                # 2.90436 mV / 4.20075 mV
    theta_tag: float = 0.2                  # 0.840149 / 4.20075
    theta_pro_default: float = 0.5          # used only when NM dependence is off
    alpha: float = 1.0
    tau_p_s: float = 3600.0
    tau_z_s: float = 3600.0
    noise: bool = True
    update_dt_ms: float = 1.0               # plasticity ODE clock (reference: neuron dt)
    # Placeholder: T-current calcium added to the postsynaptic calcium seen by every synapse.
    c_T: float = 0.5
    tau_CaT_ms: float = 50.0
    k_CaT_per_nA_ms: float = 0.05
    # theta_pro is a threshold on a SUM over incoming synapses, defined for the reference in-degree
    # (160). At in-degree K it is scaled by K/160, so it equals the published value at full size.
    scale_theta_pro_by_indegree: bool = True
    indegree_ref: float = 160.0             # 1600 * 0.1 in the reference network


class Creb(_Strict):
    tau_s: float = 600.0                    # minutes; compressed with the slow processes
    tau_Ca_soma_ms: float = 200.0
    Ca_spike: float = 0.05
    k_T_per_nA_ms: float = 0.02
    dVT_mV: float = 3.0                     # threshold lowering at creb = 1


class Neuromod(_Strict):
    tonic: float = 0.12
    tonic_ramp_to: float | None = None      # linear ramp across encode, if set
    consolidation_tonic: float = 0.12
    phasic_amp: float = 0.15
    phasic_tau_s: float = 0.5
    salience_tau_s: float = 2.0             # running-average window for the mismatch
    salience_z: float = 2.0
    salience_refractory_s: float = 1.0
    nm_ref: float = 0.12                    # gain / inhibition are neutral at this level
    k_gain: float = 2.0                     # input gain = 1 + k_gain * (NM - nm_ref)
    k_inh_pA: float = 200.0                 # inhibitory set point: bias = k * (NM - nm_ref)
    nm_max: float = 0.5
    pulse_amp: float = 0.3                  # recall mode "nm_pulse"
    pulse_s: float = 1.0


class MSO(_Strict):
    """Coincidence population on the two nerves (one MSO; ipsi = LEFT). Every number is a placeholder."""
    cf_max_hz: float = 1500.0               # phase-locking limit for fine-structure ITD (Verschooten et al. 2019)
    delays_us: list[float] = [-600, -500, -400, -300, -200, -100, 0, 100, 200, 300, 400, 500, 600]
    tau_e_ms: float = 0.2                   # EPSC
    tau_i_ms: float = 0.5                   # fast glycinergic IPSC
    inh_lead_ms: float = 0.3                # contralateral inhibition ARRIVES BEFORE contralateral excitation
    w_inh: float = 0.5                      # IPSC amplitude relative to one EPSC
    tau_m_ms: float = 0.3
    theta_epsp: float = 3.0                 # threshold in units of one EPSP
    t_ref_ms: float = 1.0


class Ephaptic(_Strict):
    """I_eph = g_eph * V_field. Fields sum LINEARLY; the nonlinearity stays in the membrane."""
    g_eph_nS: float = 0.0                   # 0 = the term is ABSENT from the equations (exact regression)
    r_field_Mohm: float = 1.0               # mean net synaptic current per cell -> field; sets a mV-scale field
    use_lfp: bool = True
    use_neurophonic: bool = True


class Theta(_Strict):
    """A pacemaker external to the network (septum-like), delivered as a current.

    off    no theta drive
    free   free-running oscillator: stimulus responses are pure EVOKED responses riding on it
    reset  the oscillator's phase is reset on envelope onsets (ENTRAINMENT by phase reset)
    """
    mode: Literal["off", "free", "reset"] = "free"
    f_hz: float = 6.0
    amp_pA: float = 40.0
    target: Literal["inh", "exc", "both"] = "inh"
    reset_phase_rad: float = 0.0
    onset_z: float = 1.5                    # envelope-derivative threshold for an onset
    onset_refractory_s: float = 0.15


class Attention(_Strict):
    """Attend one stream via NM gain: NM(t) gains a term following the attended stream's envelope,
    so input gain rises when the attended stream is active. Placeholder -- ASSUMPTIONS.md."""
    stream: int | None = None
    amp: float = 0.15


class NmExcitability(_Strict):
    """Recall-phase DRIVE, candidate 1: NM raises excitatory-cell excitability and does NOT raise inhibition.

    Basis: Bacon, Pickering & Mellor 2020, Cereb Cortex 30:6135, doi:10.1093/cercor/bhaa159 (PMC7609922):
    endogenous LC noradrenaline raises CA1 pyramidal excitation-spike coupling via beta-adrenoceptors without
    changing feedforward excitatory or inhibitory input. The classical beta-AR mechanism is block of the slow
    AHP (Madison & Nicoll 1982, cited there). Here: the AdEx adaptation current w is the AHP-like K+ current.
      ahp_scale = clip(1 - strength*ahp_block_per_nm*(NM - nm_ref), 0, 1)     multiplies w
      VT        = VT - strength*dVT_mV_per_nm*(NM - nm_ref)                   (NM above reference only)
    E cells only. The two gains were fixed BEFORE any run, from one stated anchor: at the recall NM level
    (nm_ref + pulse_amp = +0.3) the AHP is fully blocked and threshold drops 2 mV. `strength` scales both and
    is what a sweep varies; the whole sweep is reported."""
    ahp_block_per_nm: float = 1.0 / 0.3
    dVT_mV_per_nm: float = 2.0 / 0.3
    strength: float = 1.0


class IntrinsicTrace(_Strict):
    """C1. The per-cell intrinsic excitability trace IS the existing CREB-like variable (no parallel state):
    raised by encoding activity (somatic calcium), bounded to [0, 1] where it acts, slow decay. With this
    switch on it also REDUCES ADAPTATION and lowers threshold further. It gates reactivation and allocation;
    it cannot store content (one scalar per cell) -- content stays in the synapses. Placeholders."""
    k_ahp: float = Field(0.5, ge=0, le=1)   # fraction of the AHP-like current removed at trace = 1
    dVT_mV: float = 2.0                     # extra threshold lowering at trace = 1 (on top of creb.dVT_mV)


class PriorDrift(_Strict):
    """C4. The intrinsic trace erodes PER USE (each spike), independently of the synaptic write rate, so a
    prior can drift while the synaptic trace does not. `prior_repulsion` is a separate switch: a fast
    recent-use variable that RAISES threshold ("seek novel"). SIGN UNSETTLED -- the adaptation literature
    reports both attractive and repulsive tuning shifts; this implements the repulsive one only, off by default."""
    erosion_per_spike: float = Field(0.01, ge=0, le=1)
    repulsion_mV: float = 2.0
    tau_use_s: float = 5.0
    use_per_spike: float = 0.1


class MismatchGate(_Strict):
    """C2. Per cell, mismatch = |I_ff - I_rec| / (|I_ff| + |I_rec| + eps), each current low-passed over `tau_ms`;
    pooled to ONE population value M (the mean over E cells). Both currents are the cell's own synaptic
    currents -- nothing external. Three regimes gate the early-phase WRITE (induction and its noise; capture of
    already-tagged synapses is not gated):
        M < theta_low              retrieval only: plasticity off
        theta_low <= M <= theta_high   lability window for the active assembly (C3, if on; else plasticity on)
        M > theta_high             new-trace mode: plasticity scaled by the postsynaptic cell's allocation bias
                                   (its intrinsic trace, C1's variable) and BLOCKED at already-consolidated
                                   synapses (z >= z_protect) -- the existing assembly is protected
    Thresholds are placeholders; the declared sweep is in ASSUMPTIONS.md."""
    tau_ms: float = 50.0
    eps_pA: float = 1.0
    theta_low: float = 0.2
    theta_high: float = 0.6
    z_protect: float = 0.1
    creb_ref: float = 0.2


class Lability(_Strict):
    """C3. A time-limited plasticity gain on the REACTIVATED assembly, then restabilisation to baseline. A cell
    is 'reactivated' when it spikes while its own recurrent excitatory current exceeds its feedforward one -- a
    test on the cell's own currents, not on any label. Placeholders."""
    gain: float = Field(3.0, ge=1.0)
    tau_s: float = 5.0                      # restabilisation (simulated seconds; NOT time-compressed)


class Settling(_Strict):
    """C8. Recall as K cycles: the cue is re-presented each cycle and combined with the network's OWN activity from
    the previous cycle. ROUTE (a), chosen over theta-gating (b) -- see ASSUMPTIONS.md: a delayed feedback
    projection E->E whose weights are LEARNED during encoding by the same calcium/STC rule, delivered one cycle
    late, and delivering only its learned part (h - 1 + z), so an untrained projection carries nothing.
    Decoder output is never re-injected. K = 1 builds the base network exactly (no projection)."""
    k_cycles: int = Field(1, ge=1)
    cycle_gap_s: float = 1.0                # silent gap after the cue inside each cycle; period = cue + gap
    p_fb: float = 0.1
    g0_fb_nS: float = 1.0
    multi_view: bool = False                # C8b: each cycle shows a DIFFERENT subset of cue channels (same fraction)


class Mechanisms(_Strict):
    """One switch per mechanism. All True = the full model."""
    t_current: bool = True
    gap_junctions: bool = True
    nm_dynamic: bool = True                 # False = NM(t) flat at the tonic level
    tagging: bool = True                    # False = no tag, so no late phase
    creb: bool = True
    tonic_drift: bool = True
    theta: bool = True                      # False = theta.mode forced to "off"
    nm_excitability: bool = False           # recall-phase drive candidate 1 (OFF: the published-results model)
    intrinsic_trace: bool = False           # C1: the CREB-like trace also reduces adaptation / lowers threshold
    mismatch_gate: bool = False             # C2: population feedforward-vs-recurrent mismatch gates the write
    lability_window: bool = False           # C3: reactivated cells get a decaying plasticity gain
    iterative_settling: bool = False        # C8: recall in K cycles through a learned delayed feedback projection
    prior_drift: bool = False               # C4: the trace erodes per spike
    prior_repulsion: bool = False           # C4 option: recent use RAISES threshold. Sign unsettled.
    nm_inhibitory_setpoint: bool = True     # False = NM no longer biases the I cells
    plasticity: bool = True                 # False = frozen weights (a fixed spiking reservoir)


class Protocol(_Strict):
    settle_s: float = 1.0
    encode_s: float = 20.0
    # Delays are in SIMULATED seconds after the end of encoding. The biological equivalent for
    # the slow processes is delay * time_compression.
    recall_delays_s: list[float] = [5.0, 60.0]
    recall_s: float | None = None           # None = encode_s
    # nm_pulse: a 1 s NM pulse at probe onset.  nm_sustained: NM elevated by pulse_amp for the WHOLE probe.
    # cue_nm: the cue plus NM elevated for the whole probe.
    recall_mode: Literal["cue", "no_cue", "nm_pulse", "nm_sustained", "cue_nm"] = "cue"

    @property
    def cued(self) -> bool:
        return self.recall_mode in ("cue", "cue_nm")
    cue_fraction: float = Field(0.15, ge=0.0, le=1.0)
    cue_stream: int = 0
    cue_channel_fraction: float = Field(1.0, gt=0.0, le=1.0)   # C7: fraction of INPUT CHANNELS the cue drives (1 = all)
    shuffle_input: bool = False             # control: block-shuffled envelopes drive the net


class Decode(_Strict):
    rate_hz: float = 100.0
    filter_tau_ms: float = 50.0
    train_fraction: float = 0.8
    targets: list[Literal["envelope", "an_rate"]] = ["envelope"]
    alphas: list[float] = [1e-2, 1e-1, 1.0, 10.0, 100.0, 1000.0]
    engram_metric: Literal["protein", "late_weight"] = "protein"
    engram_threshold: float = 0.1
    rank_window_ms: float = 50.0
    n_surrogates: int = 200


class Eval(_Strict):
    """EVALUATION MODES -- not biology. Nothing here is a claim about a nervous system."""
    # C6 frozen read: induction, its noise and late-phase capture are switched off DURING RECALL SEGMENTS by an
    # externally imposed schedule, so a recall can be read without the read rewriting the trace. It is the
    # ground truth that lossy (plastic) reads are compared against. Passive decay continues.
    freeze_plasticity_at_recall: bool = False


class Sim(_Strict):
    dt_ms: float = 0.1
    device: Literal["cpp_standalone", "runtime"] = "cpp_standalone"
    runtime_target: Literal["numpy", "cython"] = "numpy"
    state_log_dt_ms: float = 1.0
    log_states_in: list[Literal["settle", "encode", "consolidate", "recall"]] = ["encode", "recall"]
    slow_log_dt_s: float = 1.0
    weight_log_dt_s: float = 5.0
    keep_build: bool = False
    profile: bool = False
    log_provenance: bool = False            # C5, ANALYSIS ONLY: record each spike's own I_ff and I_rec


class Config(_Strict):
    seed: int = 0
    time_compression: float = Field(60.0, ge=1.0)
    frontend: Frontend = Frontend()
    mixing: Mixing = Mixing()
    network: Network = Network()
    noise: Noise = Noise()
    drift: Drift = Drift()
    gap: GapJunctions = GapJunctions()
    plasticity: Plasticity = Plasticity()
    creb: Creb = Creb()
    neuromod: Neuromod = Neuromod()
    theta: Theta = Theta()
    nm_excitability: NmExcitability = NmExcitability()
    intrinsic_trace: IntrinsicTrace = IntrinsicTrace()
    prior_drift: PriorDrift = PriorDrift()
    mismatch_gate: MismatchGate = MismatchGate()
    lability: Lability = Lability()
    settling: Settling = Settling()
    mso: MSO = MSO()
    ephaptic: Ephaptic = Ephaptic()
    attention: Attention = Attention()
    mechanisms: Mechanisms = Mechanisms()
    protocol: Protocol = Protocol()
    decode: Decode = Decode()
    eval: Eval = Eval()
    sim: Sim = Sim()

    @model_validator(mode="after")
    def _deps(self):
        if self.settling.k_cycles > 1 and not (self.mechanisms.iterative_settling and self.protocol.cued):
            raise ValueError("settling.k_cycles > 1 needs mechanisms.iterative_settling and a cued recall mode")
        if self.mechanisms.intrinsic_trace and not self.mechanisms.creb:
            raise ValueError("mechanisms.intrinsic_trace reuses the CREB-like variable: it needs mechanisms.creb")
        return self

    @property
    def settling_active(self) -> bool:
        return self.mechanisms.iterative_settling and self.settling.k_cycles > 1

    def compression_label(self) -> str:
        return (f"time compression {self.time_compression:g}x "
                f"(slow processes only: early-phase decay, protein, late phase, CREB)")


def load_config(path: str | Path | None) -> Config:
    if path is None:
        return Config()
    data = yaml.safe_load(Path(path).read_text()) or {}
    return Config.model_validate(data)


def dump_config(cfg: Config, path: str | Path) -> None:
    Path(path).write_text(yaml.safe_dump(cfg.model_dump(), sort_keys=False))
