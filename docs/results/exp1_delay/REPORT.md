# 20260921-000259_exp1_delay

_time compression 60x (slow processes only: early-phase decay, protein, late phase, CREB)_

## Experiment 1 -- reconstruction vs delay (one stream, recall mode `cue`)

Encode held-out r: +0.832 [+0.787, +0.878] (n=10); raw-input upper bound: +0.973 [+0.965, +0.980] (n=10).

| delay (sim s) | bio-equivalent | spiking r, UNGUARDED (includes cue carry-over) | spiking r, guarded | ESN r, guarded | spiking - ESN (guarded) | best-lag p<0.05 (seeds) |
|---|---|---|---|---|---|---|
| 5.0 | 5 min | -0.025 [-0.107, +0.058] (n=10) | -0.029 [-0.146, +0.087] (n=10) | -0.027 [-0.158, +0.104] (n=10) | -0.002 [-0.209, +0.204] (n=10) does not beat | 2/10 |
| 30.0 | 30 min | -0.026 [-0.118, +0.066] (n=10) | -0.003 [-0.101, +0.094] (n=10) | -0.015 [-0.124, +0.094] (n=10) | +0.012 [-0.139, +0.163] (n=10) does not beat | 2/10 |
| 120.0 | 120 min | -0.018 [-0.103, +0.067] (n=10) | +0.038 [-0.036, +0.112] (n=10) | -0.005 [-0.118, +0.109] (n=10) | +0.043 [-0.070, +0.156] (n=10) does not beat | 2/10 |

Recall is scored on the GUARDED window (from 1 s after cue offset). The unguarded column is kept because the first pass of this experiment scored +0.045 there at EVERY delay -- carry-over of the cue, not storage.
Probes share one timeline, so an earlier probe can alter a later one.
