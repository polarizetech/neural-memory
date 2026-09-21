# 20260921-014543_attention_two_stream

_time compression 60x (slow processes only: early-phase decay, protein, late phase, CREB)_

## Attention -- attend stream 0 via NM gain

| condition | theta PLV s0 | theta PLV s1 | recall r s0 | recall r s1 | smear ms (cued s0) |
|---|---|---|---|---|---|
| no_attention | +0.381 [+0.299, +0.463] (n=10) | +0.676 [+0.616, +0.737] (n=10) | +0.039 [-0.047, +0.125] (n=10) | -0.010 [-0.037, +0.018] (n=10) | +392.000 [+266.374, +517.626] (n=10) |
| attend_stream0 | +0.393 [+0.312, +0.474] (n=10) | +0.676 [+0.614, +0.737] (n=10) | +0.035 [-0.029, +0.098] (n=10) | -0.017 [-0.044, +0.011] (n=10) | +439.000 [+340.024, +537.976] (n=10) |

- attention shifts theta locking toward the attended stream: +0.013 [+0.003, +0.024] (n=10) -> YES
- attended recall is less smeared (smear reduction, ms): -47.000 [-232.044, +138.044] (n=10) -> NOT DETECTED
