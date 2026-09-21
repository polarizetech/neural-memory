# 20260921-134920_storage_A

_time compression 60x (slow processes only: early-phase decay, protein, late phase, CREB)_

## Storage diagnostic, condition A -- calibrated rule (Graupner & Brunel 2012 hippocampal, theta_p 1.18), input->E fixed

200 E / 50 I, quick.yaml, drive off, seeds and stimuli as D4. 10 of 10 seeds complete; 0 of 20 plastic/null runs failed.

### Tags and magnitudes -- E->E (units of h_0)

| seed | synapses | END OF ENCODING tags: potentiation / depression | AFTER CONSOLIDATION tags: pot / dep | late-phase: pot / dep | frac changed (early / late) | mean abs dW (early / late / total) | max abs dW total | null (b) max abs dW, plasticity off | E rate encode Hz |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 4051 | 409 / 0 | 286 / 0 | 389 / 0 | 0.692 / 0.103 | 0.0289 / 0.0531 / 0.0820 | 1.073 | 0.0e+00 | 1.60 |
| 1 | 3917 | 464 / 0 | 320 / 0 | 426 / 0 | 0.763 / 0.119 | 0.0333 / 0.0599 / 0.0932 | 1.081 | 0.0e+00 | 2.11 |
| 2 | 3944 | 358 / 0 | 272 / 0 | 323 / 0 | 0.643 / 0.094 | 0.0272 / 0.0435 / 0.0707 | 1.073 | 0.0e+00 | 2.61 |
| 3 | 3860 | 529 / 0 | 458 / 0 | 527 / 0 | 0.726 / 0.139 | 0.0442 / 0.0859 / 0.1301 | 1.073 | 0.0e+00 | 3.63 |
| 4 | 4136 | 572 / 0 | 468 / 0 | 547 / 0 | 0.827 / 0.155 | 0.0453 / 0.0842 / 0.1296 | 1.079 | 0.0e+00 | 4.08 |
| 5 | 3900 | 347 / 0 | 315 / 0 | 330 / 0 | 0.610 / 0.094 | 0.0285 / 0.0472 / 0.0758 | 1.081 | 0.0e+00 | 2.45 |
| 6 | 3982 | 193 / 0 | 142 / 0 | 148 / 0 | 0.756 / 0.049 | 0.0158 / 0.0160 / 0.0318 | 1.076 | 0.0e+00 | 0.84 |
| 7 | 3908 | 236 / 0 | 225 / 0 | 226 / 0 | 0.738 / 0.068 | 0.0217 / 0.0310 / 0.0527 | 1.062 | 0.0e+00 | 1.28 |
| 8 | 3882 | 361 / 0 | 292 / 0 | 314 / 0 | 0.607 / 0.093 | 0.0255 / 0.0461 / 0.0716 | 1.078 | 0.0e+00 | 1.46 |
| 9 | 4074 | 448 / 0 | 307 / 0 | 407 / 0 | 0.829 / 0.113 | 0.0312 / 0.0563 / 0.0875 | 1.074 | 0.0e+00 | 1.82 |

### Stream decode, E->E (all plastic weights; the pre-registered test) -- RAW -- rank of the stored stream among 21

| seed | total | early | late |
|---|---|---|---|
| 0 | 17 (r +0.900, best foreign +0.945, >p95) | 10 (r +0.938, best foreign +0.950, >p95) | 19 (r +0.869, best foreign +0.937, >p95) |
| 1 | 2 (r +0.892, best foreign +0.906, >p95) | 3 (r +0.929, best foreign +0.933, >p95) | 2 (r +0.861, best foreign +0.884, >p95) |
| 2 | 13 (r +0.955, best foreign +0.980, >p95) | 7 (r +0.978, best foreign +0.983, >p95) | 13 (r +0.937, best foreign +0.971, >p95) |
| 3 | 16 (r +0.947, best foreign +0.974, >p95) | 13 (r +0.970, best foreign +0.982, >p95) | 18 (r +0.931, best foreign +0.966, >p95) |
| 4 | 13 (r +0.948, best foreign +0.965, >p95) | 13 (r +0.972, best foreign +0.980, >p95) | 12 (r +0.929, best foreign +0.952, >p95) |
| 5 | 1 (r +0.994, best foreign +0.994, >p95) | 2 (r +0.988, best foreign +0.988, >p95) | 2 (r +0.994, best foreign +0.995, >p95) |
| 6 | 18 (r +0.942, best foreign +0.987, >p95) | 19 (r +0.957, best foreign +0.980, >p95) | 17 (r +0.912, best foreign +0.985, >p95) |
| 7 | 19 (r +0.963, best foreign +0.988, >p95) | 19 (r +0.954, best foreign +0.975, >p95) | 19 (r +0.957, best foreign +0.984, >p95) |
| 8 | 7 (r +0.920, best foreign +0.944, >p95) | 4 (r +0.944, best foreign +0.953, >p95) | 7 (r +0.897, best foreign +0.929, >p95) |
| 9 | 7 (r +0.944, best foreign +0.958, >p95) | 5 (r +0.962, best foreign +0.971, >p95) | 7 (r +0.924, best foreign +0.948, >p95) |
| | 1st in **1/10**, mean rank 11.3, >p95 in 10/10 | 1st in **0/10**, mean rank 9.5, >p95 in 10/10 | 1st in **0/10**, mean rank 11.6, >p95 in 10/10 |

### Stream decode, E->E (all plastic weights; the pre-registered test) -- RESIDUAL -- rank of the stored stream among 21

| seed | total | early | late |
|---|---|---|---|
| 0 | 19 (r -0.306, best foreign +0.596) | 7 (r +0.111, best foreign +0.393, >p95) | 19 (r -0.416, best foreign +0.627) |
| 1 | 4 (r +0.181, best foreign +0.382, >p95) | 3 (r +0.194, best foreign +0.293, >p95) | 4 (r +0.164, best foreign +0.396, >p95) |
| 2 | 9 (r +0.172, best foreign +0.444, >p95) | 2 (r +0.386, best foreign +0.413, >p95) | 9 (r +0.145, best foreign +0.455, >p95) |
| 3 | 14 (r -0.235, best foreign +0.597) | 13 (r -0.096, best foreign +0.541) | 15 (r -0.260, best foreign +0.573) |
| 4 | 17 (r -0.152, best foreign +0.385) | 18 (r -0.152, best foreign +0.264) | 16 (r -0.128, best foreign +0.393) |
| 5 | 3 (r +0.274, best foreign +0.334, >p95) | 5 (r +0.277, best foreign +0.400, >p95) | 2 (r +0.326, best foreign +0.466, >p95) |
| 6 | 17 (r -0.470, best foreign +0.736) | 20 (r -0.348, best foreign +0.388) | 17 (r -0.468, best foreign +0.802) |
| 7 | 15 (r -0.046, best foreign +0.431) | 11 (r -0.053, best foreign +0.414) | 12 (r -0.007, best foreign +0.321) |
| 8 | 4 (r +0.270, best foreign +0.560, >p95) | 3 (r +0.280, best foreign +0.482, >p95) | 4 (r +0.275, best foreign +0.550, >p95) |
| 9 | 12 (r +0.015, best foreign +0.407) | 6 (r +0.124, best foreign +0.437, >p95) | 13 (r -0.052, best foreign +0.414) |
| | 1st in **0/10**, mean rank 11.4, >p95 in 4/10 | 1st in **0/10**, mean rank 8.8, >p95 in 6/10 | 1st in **0/10**, mean rank 11.1, >p95 in 4/10 |

### Verdict (total dW, all plastic weights, pre-first-recall)

- RAW: 1st in **1/10**, above permutation p95 in **10/10** -> **FAIL**
- RESIDUAL: 1st in **0/10**, above permutation p95 in **4/10** -> **FAIL**
