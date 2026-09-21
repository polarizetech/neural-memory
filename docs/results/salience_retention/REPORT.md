# 20260921-015751_salience_retention

_time compression 60x (slow processes only: early-phase decay, protein, late phase, CREB)_

## Salience-gated retention of a rare event

| system | event-window r | whole-stream r |
|---|---|---|
| network, salience_gated | -0.035 [-0.164, +0.095] (n=10) | -0.011 [-0.073, +0.050] (n=10) |
| network, flat_nm | +0.045 [-0.109, +0.199] (n=10) | -0.005 [-0.048, +0.039] (n=10) |
| uniform: libopus@state | +0.774 [+0.742, +0.805] (n=10) | +0.780 [+0.773, +0.787] (n=10) |
| uniform: libopus@full | +0.926 [+0.912, +0.940] (n=10) | +0.921 [+0.920, +0.922] (n=10) |
| uniform: aac@state | +0.823 [+0.766, +0.880] (n=10) | +0.863 [+0.857, +0.870] (n=10) |
| uniform: aac@full | +0.879 [+0.834, +0.924] (n=10) | +0.909 [+0.904, +0.913] (n=10) |

- gated vs flat NM, event window: -0.079 [-0.269, +0.110] (n=10) -> no detectable benefit
- gated network vs uniform Opus at the state budget, event window: -0.808 [-0.943, -0.674] (n=10) -> network LOSES or ties
- late-phase weight landing on event-active cells, above chance share: +0.026 [-0.038, +0.089] (n=10)
