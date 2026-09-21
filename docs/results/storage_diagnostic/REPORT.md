# 20260921-115553_storage_diagnostic

_time compression 60x (slow processes only: early-phase decay, protein, late phase, CREB)_

## Storage diagnostic -- is anything stream-specific written into the weights?

200 E / 50 I, quick.yaml, drive off, the recall_drive baseline seeds and stimuli. 10 of 10 seeds complete; 0 of 230 runs failed.

### D2 -- dW magnitudes (units of the baseline weight h_0), pre-encoding -> immediately before the first recall cue (120 s = 2 h of slow-process time)

| seed | synapses | frac changed: early / late / total | mean abs dW: early / late / total | max abs dW: early / late / total | tagged (potentiated) | late-phase | cells with protein | null (b) max abs dW, plasticity off |
|---|---|---|---|---|---|---|---|---|
| 0 | 4051 | 0.113 / 0.023 / 0.113 | 0.0082 / 0.0033 / 0.0115 | 0.355 / 0.358 / 0.688 | 87 (0) | 54 | 71 | 0.00e+00 |
| 1 | 3917 | 0.145 / 0.038 / 0.145 | 0.0123 / 0.0068 / 0.0192 | 0.346 / 0.360 / 0.692 | 125 (0) | 94 | 91 | 0.00e+00 |
| 2 | 3944 | 0.093 / 0.058 / 0.093 | 0.0158 / 0.0122 / 0.0280 | 0.343 / 0.359 / 0.703 | 206 (0) | 167 | 134 | 0.00e+00 |
| 3 | 3860 | 0.152 / 0.084 / 0.152 | 0.0207 / 0.0170 / 0.0377 | 0.353 / 0.361 / 0.708 | 203 (0) | 254 | 152 | 0.00e+00 |
| 4 | 4136 | 0.198 / 0.082 / 0.198 | 0.0241 / 0.0214 / 0.0455 | 0.359 / 0.360 / 0.718 | 285 (0) | 317 | 165 | 0.00e+00 |
| 5 | 3900 | 0.083 / 0.055 / 0.083 | 0.0161 / 0.0114 / 0.0275 | 0.342 / 0.358 / 0.686 | 198 (0) | 149 | 125 | 0.00e+00 |
| 6 | 3982 | 0.079 / 0.011 / 0.079 | 0.0039 / 0.0005 / 0.0044 | 0.342 / 0.301 / 0.620 | 38 (0) | 8 | 38 | 0.00e+00 |
| 7 | 3908 | 0.113 / 0.023 / 0.113 | 0.0076 / 0.0024 / 0.0100 | 0.347 / 0.356 / 0.694 | 81 (0) | 70 | 75 | 0.00e+00 |
| 8 | 3882 | 0.086 / 0.017 / 0.086 | 0.0074 / 0.0020 / 0.0094 | 0.353 / 0.344 / 0.679 | 80 (0) | 36 | 31 | 0.00e+00 |
| 9 | 4074 | 0.129 / 0.031 / 0.129 | 0.0098 / 0.0033 / 0.0131 | 0.350 / 0.359 / 0.696 | 95 (0) | 56 | 92 | 0.00e+00 |

At the END OF ENCODING (before consolidation):

| seed | frac changed (early) | mean abs early dW | max abs early dW | tagged (potentiated) |
|---|---|---|---|---|
| 0 | 0.114 | 0.0233 | 1.010 | 99 (0) |
| 1 | 0.145 | 0.0350 | 0.988 | 165 (0) |
| 2 | 0.092 | 0.0449 | 0.977 | 228 (0) |
| 3 | 0.152 | 0.0588 | 1.001 | 334 (1) |
| 4 | 0.198 | 0.0684 | 1.025 | 347 (0) |
| 5 | 0.083 | 0.0458 | 0.975 | 222 (0) |
| 6 | 0.079 | 0.0112 | 0.972 | 58 (0) |
| 7 | 0.113 | 0.0217 | 0.989 | 86 (0) |
| 8 | 0.086 | 0.0209 | 1.005 | 125 (0) |
| 9 | 0.129 | 0.0278 | 0.999 | 140 (0) |

### D3 -- stream decode: rank of the STORED stream among 21 (chance = 1/21), at the pre-first-recall snapshot

| seed | TOTAL dW (the pre-registered test) | early-phase dW | late-phase dW | predictor ceiling r (own activity): early / late / total |
|---|---|---|---|---|
| 0 | rank 4/21, r +0.893 (foreign max +0.909, perm95 +0.030, beats) | rank 3/21, r +0.925 (foreign max +0.936, perm95 +0.029, beats) | rank 4/21, r +0.785 (foreign max +0.811, perm95 +0.033, beats) | +0.999 / +0.997 / +0.999 |
| 1 | rank 12/21, r +0.984 (foreign max +0.989, perm95 +0.029, beats) | rank 10/21, r +0.982 (foreign max +0.987, perm95 +0.028, beats) | rank 12/21, r +0.975 (foreign max +0.984, perm95 +0.027, beats) | +0.999 / +0.999 / +0.999 |
| 2 | rank 16/21, r +0.987 (foreign max +0.994, perm95 +0.030, beats) | rank 15/21, r +0.986 (foreign max +0.991, perm95 +0.029, beats) | rank 16/21, r +0.982 (foreign max +0.994, perm95 +0.029, beats) | +0.999 / +0.999 / +0.999 |
| 3 | rank 3/21, r +0.986 (foreign max +0.986, perm95 +0.029, beats) | rank 6/21, r +0.987 (foreign max +0.989, perm95 +0.029, beats) | rank 1/21, r +0.979 (foreign max +0.979, perm95 +0.027, beats) | +0.999 / +0.998 / +0.999 |
| 4 | rank 18/21, r +0.986 (foreign max +0.994, perm95 +0.028, beats) | rank 15/21, r +0.989 (foreign max +0.994, perm95 +0.027, beats) | rank 19/21, r +0.979 (foreign max +0.993, perm95 +0.027, beats) | +0.999 / +0.999 / +0.999 |
| 5 | rank 15/21, r +0.980 (foreign max +0.991, perm95 +0.027, beats) | rank 13/21, r +0.984 (foreign max +0.990, perm95 +0.028, beats) | rank 15/21, r +0.970 (foreign max +0.988, perm95 +0.027, beats) | +0.999 / +0.999 / +1.000 |
| 6 | rank 19/21, r +0.988 (foreign max +0.997, perm95 +0.031, beats) | rank 20/21, r +0.991 (foreign max +0.998, perm95 +0.032, beats) | rank 21/21, r +0.931 (foreign max +0.994, perm95 +0.002, beats) | +0.999 / +0.983 / +0.998 |
| 7 | rank 8/21, r +0.991 (foreign max +0.994, perm95 +0.030, beats) | rank 7/21, r +0.990 (foreign max +0.994, perm95 +0.029, beats) | rank 7/21, r +0.977 (foreign max +0.986, perm95 +0.045, beats) | +0.999 / +0.996 / +0.999 |
| 8 | rank 3/21, r +0.960 (foreign max +0.964, perm95 +0.027, beats) | rank 2/21, r +0.977 (foreign max +0.977, perm95 +0.027, beats) | rank 1/21, r +0.896 (foreign max +0.896, perm95 +0.033, beats) | +0.999 / +0.998 / +0.999 |
| 9 | rank 4/21, r +0.973 (foreign max +0.984, perm95 +0.028, beats) | rank 4/21, r +0.986 (foreign max +0.988, perm95 +0.027, beats) | rank 5/21, r +0.906 (foreign max +0.955, perm95 +0.031, beats) | +0.999 / +0.997 / +0.999 |

At the end of encoding (early-phase dW only is meaningful there):

| seed | early-phase dW |
|---|---|
| 0 | rank 3/21, r +0.925 (foreign max +0.936, perm95 +0.029, beats) |
| 1 | rank 10/21, r +0.982 (foreign max +0.987, perm95 +0.028, beats) |
| 2 | rank 15/21, r +0.986 (foreign max +0.991, perm95 +0.029, beats) |
| 3 | rank 6/21, r +0.986 (foreign max +0.989, perm95 +0.029, beats) |
| 4 | rank 15/21, r +0.989 (foreign max +0.994, perm95 +0.027, beats) |
| 5 | rank 13/21, r +0.984 (foreign max +0.990, perm95 +0.028, beats) |
| 6 | rank 20/21, r +0.991 (foreign max +0.998, perm95 +0.033, beats) |
| 7 | rank 7/21, r +0.990 (foreign max +0.994, perm95 +0.029, beats) |
| 8 | rank 1/21, r +0.977 (foreign max +0.977, perm95 +0.027, beats) |
| 9 | rank 4/21, r +0.985 (foreign max +0.988, perm95 +0.027, beats) |

### Verdict against the pre-registered criterion (total dW, pre-first-recall)

- stored stream ranks 1st: **0 of 10** seeds (needed >= 7)
- stored-stream correlation above the permutation 95th percentile: **10 of 10** seeds (needed >= 7)
- **FAIL**
