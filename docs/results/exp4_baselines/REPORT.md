# 20260921-012543_exp4_baselines

_time compression 60x (slow processes only: early-phase decay, protein, late phase, CREB)_

## Experiment 4 -- baselines

| system | encode held-out r | recall r (last delay) |
|---|---|---|
| spiking network (full) | +0.535 [+0.508, +0.562] (n=10) | +0.002 [-0.083, +0.086] (n=10) |
| echo state network, equal units | +0.730 [+0.712, +0.747] (n=10) | -0.023 [-0.155, +0.109] (n=10) |
| shuffled-input control (floor) | -0.030 [-0.104, +0.045] (n=10) | -0.013 [-0.107, +0.080] (n=10) |
| decoder on raw input (upper bound) | +0.748 [+0.737, +0.760] (n=10) | n/a |

- spiking - ESN, encode: -0.195 [-0.222, -0.168] (n=10) -> DOES NOT beat the reservoir
- spiking - ESN, recall: +0.024 [-0.123, +0.172] (n=10) -> DOES NOT beat the reservoir
