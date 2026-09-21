"""Electrical coupling (Cx36-like gap junctions) among inhibitory cells, via Brian2 summed variables.

Biology being approximated: Cx36 gap junctions couple nearby interneurons of the same class with
steady-state coupling coefficients of roughly 0.05-0.15 (Galarreta & Hestrin 1999 Nature 402:72;
Gibson, Beierlein & Connors 1999 Nature 402:75 -- cited from memory, see ASSUMPTIONS.md). Because
the junction is a resistor into a leaky capacitor, it is a low-pass filter: slow potentials pass,
fast spikes are attenuated. tests/test_gap.py measures both.

Sparse E-E coupling is available, OFF by default, and flagged as weakly supported biologically.
The ``modulation`` scalar stands in for pH/Mg-dependent gating of the conductance.
"""
from __future__ import annotations

import numpy as np
import brian2 as b2
from brian2 import nS

GAP_MODEL = """
g_gap : siemens
I_gap_post = g_gap*gap_mod*(V_pre - V_post) : amp (summed)
"""


def conductance_for_cc(cc: float, gL_nS: float) -> float:
    """Pairwise steady-state CC = g/(g + gL)  =>  g = CC*gL/(1 - CC). In nS."""
    return cc * gL_nS / (1.0 - cc)


def ring_pairs(n: int, neighbourhood: int, p: float, rng: np.random.Generator):
    """Unordered pairs within ``neighbourhood`` on a ring, each kept with probability p."""
    pairs = []
    for i in range(n):
        for d in range(1, neighbourhood + 1):
            j = (i + d) % n
            if i != j and rng.random() < p and (j, i) not in pairs and (i, j) not in pairs:
                pairs.append((i, j))
    return pairs


def make_gap(group: b2.NeuronGroup, pairs, g_nS: float, modulation: float, name: str) -> b2.Synapses:
    syn = b2.Synapses(group, group, GAP_MODEL, namespace={"gap_mod": float(modulation)}, name=name)
    if pairs:
        i = np.array([a for a, _ in pairs] + [c for _, c in pairs])   # symmetric: both directions
        j = np.array([c for _, c in pairs] + [a for a, _ in pairs])
        syn.connect(i=i, j=j)
        syn.g_gap = g_nS * nS
    else:
        syn.connect(i=[0], j=[1])      # a summed variable needs at least one synapse to exist
        syn.g_gap = 0 * nS
    return syn
