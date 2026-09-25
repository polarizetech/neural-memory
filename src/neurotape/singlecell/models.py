"""Single-cell habituation models (Stentor coeruleus), integrated by libRoadRunner (Tellurium / SBML).

Model M1 -- receptor inactivation, Rajan & Marshall 2025 (Curr Biol, doi 10.1016/j.cub.2025.05.071), reimplemented
from the paper's Methods and the authors' MATLAB (github.com/WallaceMarshallUCSF/StentorLearningModel, v9 "the main
model used in the text"; read for reference, not copied). Time is in MINUTES (their stimuli were one per minute).

  between stimuli     dS/dt = k_syn - k_deg S + k_rec I
                      dI/dt = -(k_rec + k_deg + k_des) I          (their eq. 2 prints "- k_deg"; text and code: +)
  at a stimulus of force F on channel c:
                      P_act = io_max / (1 + exp(-scale (F - F_mid)))
                      lambda = P_act * S_c   (open channels, Poisson mean; S_c BEFORE internalisation)
                      n_min = (V_th/V_i) S_a / (1 - (V_th/V_i) S_b)
                      p_response = 1 - PoissonCDF(n_min; lambda)
                      then S_c -= k_int P_act S_c ; I_c += same
  a probe (their zero-magnitude "virtual" stimulus) evaluates p_response without internalising.

Published parameters (paper Methods): k_int 0.1, k_recycle 0.1, k_synth 0.7, k_deg 0.02, k_des 0.005, F_mid 1.5,
scale 0.6, S_a 1000, S_b 0.00025, V_thresh 0.012. V_i = 1 and io_max = 1 are the code's stated conventions (not
printed in the paper). The steady state is S* = k_syn/k_deg = 35 receptors; a response needs > n_min = 12 open.

Minimal extensions, each a switch that defaults to the published model:
  * n_channels      independent receptor pools (modality A, B, ...) converging on one membrane. Published: 1.
  * mechanism       "internalisation" (published) | "gating" (Wood 1988: receptors are modified in place -- their
                    voltage dependence shifts -- and are neither destroyed nor internalised; the modified pool M
                    reverts at k_rec and turns over only at the basal k_deg, like any membrane protein).
  * synthesis_scale multiplies k_syn from a set time (the protein-synthesis block).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal

SOURCE_RM2025 = "Rajan & Marshall 2025, Curr Biol, doi 10.1016/j.cub.2025.05.071 [FT: Methods + authors' MATLAB v9]"


@dataclass(frozen=True)
class RMParams:
    k_int: float = 0.1          # [LIT] fraction of ACTIVATED surface receptors internalised per stimulus
    k_rec: float = 0.1          # [LIT] /min
    k_syn: float = 0.7          # [LIT] receptors/min
    k_deg: float = 0.02         # [LIT] /min, basal turnover of both pools
    k_des: float = 0.005        # [LIT] /min, destruction of internalised receptors
    F_mid: float = 1.5          # [LIT]
    scale: float = 0.6          # [LIT]
    io_max: float = 1.0         # [CODE convention]
    S_a: float = 1000.0         # [LIT] basal membrane conductance (normalised)
    S_b: float = 0.00025        # [LIT] conductance per open channel
    V_th: float = 0.012         # [LIT]
    V_i: float = 1.0            # [CODE convention: "keep Vi = 1"]

    @property
    def n_min(self) -> float:
        r = self.V_th / self.V_i
        return r * self.S_a / (1.0 - r * self.S_b)

    @property
    def S_star(self) -> float:
        return self.k_syn / self.k_deg


@dataclass(frozen=True)
class CellConfig:
    params: RMParams = field(default_factory=RMParams)
    n_channels: int = 1                                             # published: one mechanoreceptor pool
    mechanism: Literal["internalisation", "gating"] = "internalisation"
    synthesis_scale: float = 1.0                                     # 1 = published (no block)
    block_from_min: float = 0.0                                      # block applies from this time on

    def to_dict(self) -> dict:
        d = asdict(self)
        d["params"]["n_min"] = self.params.n_min
        d["params"]["S_star"] = self.params.S_star
        return d


def antimony(cfg: CellConfig) -> str:
    """The continuous (between-stimulus) dynamics as an Antimony model, one receptor pool pair per channel.
    Stimuli are discrete jumps applied by the protocol runner (as in the authors' code), not SBML events."""
    p = cfg.params
    lines = ["model stentor_cell"]
    for c in range(cfg.n_channels):
        if cfg.mechanism == "internalisation":
            lines += [f"  -> S{c}; k_syn*syn",
                      f"  S{c} -> ; k_deg*S{c}",
                      f"  I{c} -> S{c}; k_rec*I{c}",
                      f"  I{c} -> ; (k_deg + k_des)*I{c}"]
        else:  # gating: modified-in-place pool M reverts at k_rec, turns over at basal k_deg, never destroyed
            lines += [f"  -> S{c}; k_syn*syn",
                      f"  S{c} -> ; k_deg*S{c}",
                      f"  I{c} -> S{c}; k_rec*I{c}",
                      f"  I{c} -> ; k_deg*I{c}"]
        lines += [f"  S{c} = {p.S_star}; I{c} = 0"]
    lines += [f"  k_syn = {p.k_syn}; k_deg = {p.k_deg}; k_rec = {p.k_rec}; k_des = {p.k_des}",
              "  syn = 1", "end"]
    return "\n".join(lines)
