# 20260921-132149_residual_decode

_time compression 60x (slow processes only: early-phase decay, protein, late phase, CREB)_

## P0 -- residual decode of the D4 data

Observed dW: D4's own saved arrays, untouched. Predictions: the frozen-activity bank, current rule. Cells: rank of the stored stream among 21 (r stored, best foreign; '>p95' = above the permutation 95th percentile).

### Raw decode (reproduces D4)

| seed | total | early | late |
|---|---|---|---|
| 0 | 4 (r +0.893, best foreign +0.909, >p95) | 3 (r +0.925, best foreign +0.936, >p95) | 4 (r +0.785, best foreign +0.811, >p95) |
| 1 | 12 (r +0.984, best foreign +0.989, >p95) | 10 (r +0.982, best foreign +0.987, >p95) | 12 (r +0.975, best foreign +0.984, >p95) |
| 2 | 16 (r +0.987, best foreign +0.994, >p95) | 15 (r +0.986, best foreign +0.991, >p95) | 16 (r +0.982, best foreign +0.994, >p95) |
| 3 | 3 (r +0.986, best foreign +0.986, >p95) | 6 (r +0.987, best foreign +0.989, >p95) | 1 (r +0.979, best foreign +0.979, >p95) |
| 4 | 18 (r +0.986, best foreign +0.995, >p95) | 15 (r +0.989, best foreign +0.994, >p95) | 19 (r +0.979, best foreign +0.993, >p95) |
| 5 | 15 (r +0.980, best foreign +0.991, >p95) | 14 (r +0.984, best foreign +0.990, >p95) | 15 (r +0.970, best foreign +0.988, >p95) |
| 6 | 19 (r +0.988, best foreign +0.997, >p95) | 20 (r +0.990, best foreign +0.998, >p95) | 21 (r +0.930, best foreign +0.994, >p95) |
| 7 | 8 (r +0.991, best foreign +0.994, >p95) | 7 (r +0.990, best foreign +0.994, >p95) | 7 (r +0.977, best foreign +0.986, >p95) |
| 8 | 3 (r +0.960, best foreign +0.964, >p95) | 2 (r +0.977, best foreign +0.977, >p95) | 1 (r +0.896, best foreign +0.896, >p95) |
| 9 | 4 (r +0.973, best foreign +0.984, >p95) | 4 (r +0.985, best foreign +0.988, >p95) | 5 (r +0.905, best foreign +0.955, >p95) |
| | 1st in **0/10**, mean rank 10.2, >p95 in 10/10 | 1st in **0/10**, mean rank 9.6, >p95 in 10/10 | 1st in **2/10**, mean rank 10.1, >p95 in 10/10 |

### RESIDUAL decode -- the mean of the 21 predictions removed from the observed dW and from every prediction

| seed | total | early | late |
|---|---|---|---|
| 0 | 2 (r +0.602, best foreign +0.715, >p95) | 2 (r +0.543, best foreign +0.701, >p95) | 2 (r +0.537, best foreign +0.646, >p95) |
| 1 | 9 (r +0.103, best foreign +0.390, >p95) | 13 (r +0.035, best foreign +0.397, >p95) | 7 (r +0.193, best foreign +0.382, >p95) |
| 2 | 15 (r -0.011, best foreign +0.322) | 9 (r +0.045, best foreign +0.280, >p95) | 14 (r -0.006, best foreign +0.410) |
| 3 | 3 (r +0.318, best foreign +0.379, >p95) | 4 (r +0.198, best foreign +0.462, >p95) | 1 (r +0.391, best foreign +0.383, >p95) |
| 4 | 20 (r -0.225, best foreign +0.465) | 14 (r -0.046, best foreign +0.389) | 20 (r -0.320, best foreign +0.628) |
| 5 | 18 (r -0.399, best foreign +0.843) | 18 (r -0.299, best foreign +0.696) | 19 (r -0.449, best foreign +0.823) |
| 6 | 3 (r +0.677, best foreign +0.803, >p95) | 5 (r +0.160, best foreign +0.483, >p95) | 2 (r +0.922, best foreign +0.955, >p95) |
| 7 | 6 (r +0.372, best foreign +0.635, >p95) | 7 (r +0.228, best foreign +0.676, >p95) | 7 (r +0.356, best foreign +0.677, >p95) |
| 8 | 1 (r +0.683, best foreign +0.609, >p95) | 1 (r +0.682, best foreign +0.645, >p95) | 1 (r +0.654, best foreign +0.586, >p95) |
| 9 | 7 (r +0.086, best foreign +0.793, >p95) | 6 (r +0.113, best foreign +0.466, >p95) | 7 (r +0.043, best foreign +0.850, >p95) |
| | 1st in **1/10**, mean rank 8.4, >p95 in 7/10 | 1st in **1/10**, mean rank 7.9, >p95 in 8/10 | 1st in **2/10**, mean rank 8.0, >p95 in 7/10 |

**Pre-registered pass (stored stream 1st in >= 7/10 seeds, total dW): FAIL** -- 1/10.
