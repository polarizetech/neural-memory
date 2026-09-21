## Ablations, encode side (computed from runs.json by collect.py)

| condition | full - this, ENCODE held-out r | LOADED frac | late-phase synapse frac |
|---|---|---|---|
| full | +0.000 [+0.000, +0.000] (n=10) - | 0.170 | 0.0382 |
| no_t_current | -0.004 [-0.028, +0.020] (n=10) no detectable effect | 0.171 | 0.0387 |
| no_gap_junctions | +0.022 [-0.027, +0.071] (n=10) no detectable effect | 0.186 | 0.0361 |
| flat_nm | +0.026 [-0.005, +0.058] (n=10) no detectable effect | 0.128 | 0.0251 |
| no_tagging | -0.003 [-0.034, +0.027] (n=10) no detectable effect | 0.169 | 0.0000 |
| no_creb | +0.018 [-0.026, +0.063] (n=10) no detectable effect | 0.169 | 0.0385 |
| no_tonic_drift | +0.026 [-0.036, +0.088] (n=10) no detectable effect | 0.169 | 0.0383 |
| no_theta | +0.004 [-0.030, +0.038] (n=10) no detectable effect | 0.169 | 0.0399 |
| frozen_weights_reservoir | +0.009 [-0.022, +0.040] (n=10) no detectable effect | 0.166 | 0.0000 |
| filterbank_frontend | +0.105 [+0.066, +0.143] (n=10) mechanism HELPS encoding | 0.195 | 0.0302 |
