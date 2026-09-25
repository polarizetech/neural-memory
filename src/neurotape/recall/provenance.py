"""C5 -- provenance of recall-phase spikes. ANALYSIS ONLY: the network never sees any of this.

Each E spike carries the cell's own feedforward (external input) and recurrent excitatory current at the
moment it fired. A spike is labelled RECURRENTLY RECONSTRUCTED when its recurrent current exceeded its
feedforward one, and CUE-DRIVEN otherwise. The reconstructed fraction of a recall window is the share of
spikes the network supplied itself -- the quantity a completion claim has to be about."""
from __future__ import annotations



def reconstructed_fraction(res, t0: float, t1: float) -> dict:
    if res.spike_Iff is None:
        return dict(available=False, reason="sim.log_provenance is off")
    t = res.spikes_e[1]; sel = (t >= t0) & (t < t1)
    n = int(sel.sum())
    if n == 0:
        return dict(available=True, n_spikes=0, reconstructed_fraction=float("nan"), cue_driven_fraction=float("nan"))
    rec = res.spike_Irec[sel] > res.spike_Iff[sel]
    return dict(available=True, n_spikes=n, reconstructed_fraction=float(rec.mean()), cue_driven_fraction=float(1.0 - rec.mean()))
