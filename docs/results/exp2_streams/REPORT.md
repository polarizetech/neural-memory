# 20260921-002616_exp2_streams

_time compression 60x (slow processes only: early-phase decay, protein, late phase, CREB)_

## Experiment 2 -- simultaneous streams

### 2_streams

| stream | encode held-out r | recall r (last delay) | ESN recall r |
|---|---|---|---|
| 0 | +0.813 [+0.760, +0.866] (n=10) | -0.004 [-0.113, +0.106] (n=10) | -0.023 [-0.155, +0.109] (n=10) |
| 1 | +0.279 [+0.219, +0.338] (n=10) | -0.024 [-0.042, -0.005] (n=10) | -0.011 [-0.037, +0.014] (n=10) |

Encode crosstalk (rows decoded, cols true):

```
[[0.813 0.137]
 [0.255 0.279]]
```
Recall crosstalk:

```
[[-0.011 -0.009]
 [ 0.012 -0.009]]
```
- stream identity from **rank**: accuracy +0.774 [+0.757, +0.790] (n=10); permutation-null 95th pct +0.568 [+0.563, +0.573] (n=10); p<0.05 in 10/10 seeds
- stream identity from **fired**: accuracy +0.658 [+0.618, +0.698] (n=10); permutation-null 95th pct +0.572 [+0.567, +0.577] (n=10); p<0.05 in 9/10 seeds

### 3_streams

| stream | encode held-out r | recall r (last delay) | ESN recall r |
|---|---|---|---|
| 0 | +0.475 [+0.242, +0.709] (n=10) | -0.038 [-0.119, +0.044] (n=10) | +0.030 [-0.077, +0.137] (n=10) |
| 1 | +0.134 [+0.089, +0.180] (n=10) | -0.005 [-0.025, +0.015] (n=10) | +0.001 [-0.024, +0.026] (n=10) |
| 2 | +0.750 [+0.664, +0.837] (n=10) | +0.027 [-0.041, +0.094] (n=10) | -0.004 [-0.089, +0.081] (n=10) |

Encode crosstalk (rows decoded, cols true):

```
[[0.475 0.047 0.398]
 [0.125 0.134 0.019]
 [0.39  0.086 0.75 ]]
```
Recall crosstalk:

```
[[-0.024 -0.011 -0.007]
 [-0.032 -0.012  0.037]
 [ 0.013 -0.007  0.005]]
```
- stream identity from **rank**: accuracy +0.776 [+0.759, +0.793] (n=10); permutation-null 95th pct +0.402 [+0.399, +0.405] (n=10); p<0.05 in 10/10 seeds
- stream identity from **fired**: accuracy +0.581 [+0.534, +0.628] (n=10); permutation-null 95th pct +0.399 [+0.397, +0.401] (n=10); p<0.05 in 10/10 seeds

