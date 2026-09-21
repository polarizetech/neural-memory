# 20260921-003753_exp3_ablations

_time compression 60x (slow processes only: early-phase decay, protein, late phase, CREB)_

## Experiment 3 -- single-mechanism ablations

A mechanism is said to help ONLY if the whole 95% CI of (full - ablated) is above zero.

| condition | encode held-out r | recall r (last delay) | full - this (recall) | verdict |
|---|---|---|---|---|
| full | +0.548 [+0.511, +0.585] (n=10) | +0.025 [-0.070, +0.120] (n=10) | - | - |
| no_t_current | +0.552 [+0.520, +0.584] (n=10) | -0.021 [-0.083, +0.041] (n=10) | +0.046 [-0.069, +0.160] (n=10) | no detectable effect |
| no_gap_junctions | +0.526 [+0.470, +0.583] (n=10) | -0.022 [-0.107, +0.063] (n=10) | +0.046 [-0.032, +0.125] (n=10) | no detectable effect |
| flat_nm | +0.522 [+0.484, +0.560] (n=10) | +0.063 [-0.030, +0.155] (n=10) | -0.038 [-0.118, +0.043] (n=10) | no detectable effect |
| no_tagging | +0.552 [+0.523, +0.581] (n=10) | +0.011 [-0.076, +0.098] (n=10) | +0.014 [-0.115, +0.143] (n=10) | no detectable effect |
| no_creb | +0.530 [+0.476, +0.584] (n=10) | -0.012 [-0.088, +0.065] (n=10) | +0.036 [-0.027, +0.100] (n=10) | no detectable effect |
| no_tonic_drift | +0.522 [+0.457, +0.587] (n=10) | +0.038 [-0.041, +0.117] (n=10) | -0.013 [-0.159, +0.132] (n=10) | no detectable effect |
| no_theta | +0.544 [+0.515, +0.573] (n=10) | -0.020 [-0.088, +0.047] (n=10) | +0.045 [-0.097, +0.187] (n=10) | no detectable effect |
| frozen_weights_reservoir | +0.539 [+0.492, +0.586] (n=10) | +0.010 [-0.070, +0.091] (n=10) | +0.014 [-0.057, +0.086] (n=10) | no detectable effect |
| filterbank_frontend | +0.444 [+0.397, +0.490] (n=10) | +0.006 [-0.050, +0.062] (n=10) | +0.019 [-0.128, +0.165] (n=10) | no detectable effect |
