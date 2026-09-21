# 20260920-233619_exp1_delay

_time compression 60x (slow processes only: early-phase decay, protein, late phase, CREB)_

## Experiment 1 -- reconstruction vs delay (one stream, recall mode `cue`)

Encode held-out r: +0.818 [+0.771, +0.865] (n=10); raw-input upper bound: +0.978 [+0.975, +0.981] (n=10).

| delay (sim s) | bio-equivalent | spiking r | ESN r | spiking - ESN | best-lag p<0.05 (seeds) |
|---|---|---|---|---|---|
| 5.0 | 5 min | +0.048 [+0.033, +0.063] (n=10) | -0.012 [-0.050, +0.027] (n=10) | +0.060 [+0.025, +0.094] (n=10) BEATS | 1/10 |
| 30.0 | 30 min | +0.043 [+0.028, +0.059] (n=10) | -0.012 [-0.050, +0.027] (n=10) | +0.055 [+0.011, +0.099] (n=10) BEATS | 1/10 |
| 120.0 | 120 min | +0.044 [+0.036, +0.052] (n=10) | -0.012 [-0.050, +0.026] (n=10) | +0.055 [+0.017, +0.093] (n=10) BEATS | 3/10 |

Probes share one timeline, so an earlier probe can alter a later one.
