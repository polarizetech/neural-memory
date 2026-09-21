"""Storage diagnostic -- is anything stream-specific written into the weights at all?  ANALYSIS ONLY.

D2  magnitudes: what changed between the pre-encoding snapshot and a later one, early phase (h) and late
    phase (z) kept separate, in units of the baseline weight h_0 = 1.
D3  stream decode: correlate the observed dW with the dW each of 21 streams (the stored one + the same 20
    foreign streams used as the recall null) WOULD have written, predicted from that stream's own activity in
    a plasticity-frozen run by integrating the SAME calcium / early-phase / protein / capture equations the
    network uses (plasticity/stc.py), noise term omitted.
"""
from __future__ import annotations

import numpy as np

NOISE_FLOOR = 1e-6          # |dW| in units of h_0. With no threshold crossing h stays at exactly 1, so this is generous.


def snapshot(res, label: str) -> tuple[np.ndarray, np.ndarray]:
    s = res.extra["snapshots"]; k = s["labels"].index(label)
    return s["h"][:, k], s["z"][:, k]


def magnitudes(res, cfg, after: str = "pre_first_recall") -> dict:
    h0, z0 = snapshot(res, "pre_encode"); h1, z1 = snapshot(res, after)
    dh, dz = h1 - h0, z1 - z0; dw = dh + dz
    out = dict(n_synapses=int(dh.size), snapshot=after)
    for name, d in (("early", dh), ("late", dz), ("total", dw)):
        a = np.abs(d)
        out[name] = dict(frac_changed=float((a > NOISE_FLOOR).mean()), mean_abs=float(a.mean()), max_abs=float(a.max()),
                         mean_signed=float(d.mean()))
    out["n_tagged"] = int((np.abs(h1 - 1.0) > cfg.plasticity.theta_tag).sum())
    out["n_tagged_potentiated"] = int(((h1 - 1.0) > cfg.plasticity.theta_tag).sum())
    out["n_late_phase"] = int((np.abs(z1) > 0.05).sum())
    out["n_cells_protein"] = int((res.p.max(axis=1) > 0.01).sum())
    return out
