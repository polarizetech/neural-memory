# 20260921-064238_recall_modes

_time compression 60x (slow processes only: early-phase decay, protein, late phase, CREB)_

## Recall modes -- partial cue vs spontaneous replay vs NM pulse (one stream)

Uncued modes have no time reference, so the statistic that matters for them is the BEST-LAG r. It is tested two ways: against a circular shift of the true envelope (DEGENERATE for uncued modes -- the lag search spans the record, so the shifted copy is searched over the same alignments) and against 20 FOREIGN streams from the same generator (is recall closer to ITS stream than to others?), which is the test that can actually answer. `pattern r` asks the rate-pattern question instead: do the cells that fired during encoding fire during recall? Its baseline is the same correlation for the pre-encoding settle period.

### `cue`

| delay (sim s) | recall E rate (Hz) | spikes in window | time-locked r (guarded) | best-lag r | shift-null 95th pct | shift p<0.05 (seeds) | foreign-stream r (mean) | own - foreign | foreign p<0.05 (seeds) | ordering rho | pattern r | ESN time-locked r |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5.0 | +0.008 [+0.005, +0.012] (n=10) | 10 | -0.024 [-0.120, +0.071] (n=10) | +0.213 [+0.163, +0.264] (n=10) | +0.221 [+0.186, +0.256] (n=10) | 6/10 | +0.180 [+0.161, +0.200] (n=10) | +0.033 [-0.008, +0.074] (n=10) | 1/10 | +0.125 [-0.055, +0.305] (n=10) | +0.062 [-0.045, +0.170] (n=10) | -0.027 [-0.158, +0.104] (n=10) |
| 30.0 | +0.011 [+0.010, +0.013] (n=10) | 15 | +0.001 [-0.057, +0.060] (n=10) | +0.181 [+0.145, +0.218] (n=10) | +0.243 [+0.203, +0.282] (n=10) | 1/10 | +0.170 [+0.148, +0.192] (n=10) | +0.011 [-0.027, +0.050] (n=10) | 0/10 | +0.210 [+0.024, +0.397] (n=10) | +0.039 [-0.030, +0.108] (n=10) | -0.015 [-0.124, +0.094] (n=10) |
| 120.0 | +0.010 [+0.008, +0.012] (n=10) | 13 | -0.029 [-0.127, +0.069] (n=10) | +0.207 [+0.164, +0.251] (n=10) | +0.240 [+0.212, +0.269] (n=10) | 3/10 | +0.179 [+0.161, +0.198] (n=10) | +0.028 [-0.013, +0.069] (n=10) | 1/10 | -0.101 [-0.385, +0.184] (n=10) | -0.014 [-0.047, +0.019] (n=10) | -0.005 [-0.118, +0.109] (n=10) |

- pattern r, settle baseline: -0.019 [-0.056, +0.018] (n=2); recall (last delay) - baseline: +0.029 [-0.743, +0.800] (n=2) -> no reactivation above baseline
- best-lag seeds at p<0.05: expect ~0.5 of 10 by chance at each delay

### `no_cue`

| delay (sim s) | recall E rate (Hz) | spikes in window | time-locked r (guarded) | best-lag r | shift-null 95th pct | shift p<0.05 (seeds) | foreign-stream r (mean) | own - foreign | foreign p<0.05 (seeds) | ordering rho | pattern r | ESN time-locked r |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5.0 | +0.007 [+0.005, +0.009] (n=10) | 12 | -0.018 [-0.120, +0.083] (n=10) | +0.250 [+0.208, +0.293] (n=10) | +0.327 [+0.267, +0.386] (n=10) | 1/10 | +0.270 [+0.238, +0.303] (n=10) | -0.020 [-0.043, +0.003] (n=10) | 0/10 | +0.025 [-0.069, +0.120] (n=10) | +0.060 [-0.047, +0.167] (n=10) | +0.003 [-0.085, +0.091] (n=10) |
| 30.0 | +0.010 [+0.008, +0.011] (n=10) | 17 | -0.036 [-0.095, +0.024] (n=10) | +0.247 [+0.217, +0.278] (n=10) | +0.324 [+0.284, +0.364] (n=10) | 2/10 | +0.265 [+0.241, +0.288] (n=10) | -0.018 [-0.062, +0.027] (n=10) | 1/10 | +0.064 [-0.114, +0.241] (n=10) | +0.017 [-0.052, +0.087] (n=10) | -0.017 [-0.087, +0.053] (n=10) |
| 120.0 | +0.009 [+0.007, +0.011] (n=10) | 16 | +0.004 [-0.071, +0.078] (n=10) | +0.242 [+0.212, +0.272] (n=10) | +0.303 [+0.252, +0.353] (n=10) | 2/10 | +0.269 [+0.244, +0.295] (n=10) | -0.027 [-0.047, -0.008] (n=10) | 0/10 | -0.165 [-0.429, +0.100] (n=10) | -0.001 [-0.030, +0.028] (n=10) | -0.011 [-0.075, +0.052] (n=10) |

- pattern r, settle baseline: -0.019 [-0.056, +0.018] (n=2); recall (last delay) - baseline: +0.003 [-0.379, +0.386] (n=2) -> no reactivation above baseline
- best-lag seeds at p<0.05: expect ~0.5 of 10 by chance at each delay

### `nm_pulse`

| delay (sim s) | recall E rate (Hz) | spikes in window | time-locked r (guarded) | best-lag r | shift-null 95th pct | shift p<0.05 (seeds) | foreign-stream r (mean) | own - foreign | foreign p<0.05 (seeds) | ordering rho | pattern r | ESN time-locked r |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5.0 | +0.006 [+0.004, +0.008] (n=10) | 12 | -0.018 [-0.120, +0.084] (n=10) | +0.251 [+0.208, +0.294] (n=10) | +0.321 [+0.258, +0.384] (n=10) | 1/10 | +0.272 [+0.238, +0.305] (n=10) | -0.020 [-0.043, +0.002] (n=10) | 0/10 | +0.177 [+0.073, +0.282] (n=10) | +0.059 [-0.046, +0.164] (n=10) | +0.003 [-0.085, +0.091] (n=10) |
| 30.0 | +0.009 [+0.007, +0.010] (n=10) | 17 | -0.029 [-0.081, +0.023] (n=10) | +0.260 [+0.227, +0.293] (n=10) | +0.318 [+0.275, +0.360] (n=10) | 2/10 | +0.264 [+0.235, +0.292] (n=10) | -0.004 [-0.044, +0.037] (n=10) | 1/10 | +0.185 [+0.043, +0.328] (n=10) | +0.020 [-0.052, +0.091] (n=10) | -0.017 [-0.087, +0.053] (n=10) |
| 120.0 | +0.008 [+0.006, +0.010] (n=10) | 16 | -0.011 [-0.087, +0.066] (n=10) | +0.255 [+0.228, +0.282] (n=10) | +0.314 [+0.273, +0.354] (n=10) | 2/10 | +0.267 [+0.243, +0.291] (n=10) | -0.012 [-0.037, +0.013] (n=10) | 0/10 | -0.007 [-0.309, +0.295] (n=10) | +0.000 [-0.029, +0.029] (n=10) | -0.011 [-0.075, +0.052] (n=10) |

- pattern r, settle baseline: -0.019 [-0.056, +0.018] (n=2); recall (last delay) - baseline: +0.003 [-0.380, +0.387] (n=2) -> no reactivation above baseline
- best-lag seeds at p<0.05: expect ~0.5 of 10 by chance at each delay

