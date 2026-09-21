"""P1 -- the plasticity rule in isolation: one presynaptic cell, one postsynaptic cell, NO network, NO noise.

The harness drives the model's ACTUAL synapse equations (stc.plastic_model / ON_PRE / ON_POST / namespace / delays --
the same objects the network uses) with imposed pre and post spike times, at time compression 1 (the true rule).
All protocols run as independent pairs inside one Brian2 build.

Standard induction protocols and their textbook outcomes (written into tests/test_plasticity_protocols.py BEFORE
the first run):
  a  theta-burst: 10 bursts of 4 pulses at 100 Hz, bursts at 5 Hz            -> potentiation
  b  HFS: 100 Hz for 1 s                                                     -> potentiation, + late-phase capture
                                                                                when protein is available
  c  pairing pre->post +10 ms, 60 pairings at 1 Hz                           -> potentiation
  d  pairing post->pre -10 ms, 60 pairings at 1 Hz                           -> depression
  e  LFS: 1 Hz x 900 pulses                                                  -> depression
Decisions the brief left open, fixed before the first run: potentiation / depression = dh >= +0.1 / <= -0.1 h_0,
read 10 s after the protocol ends; in the afferent protocols (a, b) the postsynaptic cell fires 5 ms after each
pulse (the pre-only variant is reported beside it and does not decide pass/fail); LFS is pre-only; capture = z > 0.05
about 16 min after HFS with the protein pool held available (p = 1), and z = 0 with it empty.
"""
from __future__ import annotations

import shutil
import tempfile

import numpy as np

from ..config import Config
from . import stc

EXPECTED = {"a_tbs": "potentiation", "b_hfs": "potentiation", "c_pair_pre_post": "potentiation", "d_pair_post_pre": "depression", "e_lfs": "depression"}
T0, POST_LAG, READ_AFTER = 1.0, 0.005, 10.0

# Published parameter sets for this rule family. h-form (Luboeinski & Tetzlaff) throughout; only the calcium
# amplitudes, thresholds, time constants, rates and delay differ. Read depth is stated in ASSUMPTIONS.md.
PARAMETER_SETS = {
    "current (Luboeinski & Tetzlaff 2021)": dict(Ca_pre=0.6, Ca_post=0.1655, theta_p=3.0, theta_d=1.2, tau_Ca_ms=48.8, t_Ca_delay_ms=18.8, gamma_p=1645.6, gamma_d=313.1, tau_h_s=688.4),
    "Graupner & Brunel 2012, hippocampal slices": dict(Ca_pre=1.0, Ca_post=0.275865, theta_p=1.3, theta_d=1.0, tau_Ca_ms=48.8373, t_Ca_delay_ms=18.8008, gamma_p=1645.59, gamma_d=313.0965, tau_h_s=688.355),
    "Graupner & Brunel 2012, cortical slices": dict(Ca_pre=0.5617539, Ca_post=1.23964, theta_p=1.3, theta_d=1.0, tau_Ca_ms=22.6936, t_Ca_delay_ms=4.6098, gamma_p=725.085, gamma_d=331.909, tau_h_s=346.3615),
}


def schedules() -> dict:
    tbs = np.concatenate([T0 + b * 0.2 + np.arange(4) * 0.01 for b in range(10)])
    hfs = T0 + np.arange(100) * 0.01; pair = T0 + np.arange(60) * 1.0; lfs = T0 + np.arange(900) * 1.0
    return {                                   # name: (pre times, post times, protein available)
        "a_tbs": (tbs, tbs + POST_LAG, False), "a_tbs_pre_only": (tbs, np.array([]), False),
        "b_hfs": (hfs, hfs + POST_LAG, False), "b_hfs_pre_only": (hfs, np.array([]), False), "b_hfs_with_protein": (hfs, hfs + POST_LAG, True),
        "c_pair_pre_post": (pair, pair + 0.010, False), "d_pair_post_pre": (pair, pair - 0.010, False), "e_lfs": (lfs, np.array([]), False),
    }


def run_protocols(params: dict | None = None, cfg: Config | None = None) -> dict:
    import brian2 as b2
    from brian2 import ms, second
    cfg = (cfg or Config()).model_copy(deep=True); cfg.time_compression = 1.0; cfg.plasticity.noise = False
    for k, v in (params or {}).items():
        setattr(cfg.plasticity, k, v)
    sch = schedules(); names = list(sch); n = len(names)
    bd = tempfile.mkdtemp(prefix="brian_build_calib_")
    # order matters when the previous device was the runtime one (pytest): select standalone FIRST, then reinit it
    b2.set_device("cpp_standalone", build_on_run=False, directory=bd); b2.device.reinit(); b2.device.activate(build_on_run=False, directory=bd)
    b2.prefs["devices.cpp_standalone.extra_make_args_unix"] = ["-j3"]
    b2.start_scope(); b2.defaultclock.dt = 0.1 * ms

    def gen(which, name):
        i = np.concatenate([np.full(len(sch[k][which]), j, int) for j, k in enumerate(names)]); t = np.concatenate([sch[k][which] for k in names])
        o = np.argsort(t, kind="stable"); return b2.SpikeGeneratorGroup(n, i[o], t[o] * second, name=name)
    pre, drv = gen(0, "cal_pre"), gen(1, "cal_drv")
    post = b2.NeuronGroup(n, "fire : 1\nCaT : 1\np : 1\nsum_h_diff : 1\ng_e : siemens", threshold="fire > 0.5", reset="fire = 0", name="cal_post")
    post.p = [1.0 if sch[k][2] else 0.0 for k in names]
    kick = b2.Synapses(drv, post, on_pre="fire_post = 1", name="cal_kick"); kick.connect(i=np.arange(n), j=np.arange(n))
    syn = b2.Synapses(pre, post, stc.plastic_model(cfg), on_pre=stc.ON_PRE, on_post=stc.ON_POST, delay=stc.delays(cfg), method="heun",
                      namespace=stc.namespace(cfg), dt=cfg.plasticity.update_dt_ms * ms, name="cal_syn")
    syn.connect(i=np.arange(n), j=np.arange(n)); syn.h = 1.0
    mon = b2.StateMonitor(syn, ["h", "z"], record=np.arange(n), dt=1 * second, name="cal_mon")
    total = T0 + 900.0 + 70.0
    b2.Network(pre, drv, post, kick, syn, mon).run(total * second)
    b2.device.build(directory=bd, compile=True, run=True, debug=False, clean=False)
    t = np.array(mon.t / second); h = np.array(mon.h); z = np.array(mon.z); out = {}
    for j, k in enumerate(names):
        end = max(np.max(sch[k][0]), np.max(sch[k][1]) if len(sch[k][1]) else 0.0)
        kk = int(np.searchsorted(t, end + READ_AFTER)); dh = float(h[j, kk] - 1.0)
        out[k] = dict(dh=dh, z_end=float(z[j, -1]), outcome="potentiation" if dh >= 0.1 else ("depression" if dh <= -0.1 else "no change"))
    shutil.rmtree(bd, ignore_errors=True)
    return out


def table(results: dict) -> tuple[str, int]:
    rows, n_pass = "| protocol | expected | dh (h_0) | outcome | pass |\n|---|---|---|---|---|\n", 0
    for k, exp in EXPECTED.items():
        ok = results[k]["outcome"] == exp; n_pass += ok
        rows += f"| {k} | {exp} | {results[k]['dh']:+.3f} | {results[k]['outcome']} | {'PASS' if ok else 'FAIL'} |\n"
    cap = results["b_hfs_with_protein"]["z_end"] > 0.05 and results["b_hfs"]["z_end"] == 0.0
    rows += f"| b capture (protein available / empty) | z > 0.05 / z = 0 | {results['b_hfs_with_protein']['z_end']:+.3f} / {results['b_hfs']['z_end']:+.3f} | | {'PASS' if cap else 'FAIL'} |\n"
    rows += f"| (pre-only, not scored) a / b | | {results['a_tbs_pre_only']['dh']:+.3f} / {results['b_hfs_pre_only']['dh']:+.3f} | | |\n"
    return rows, n_pass + int(cap)
