# 20260921-020516_exp5_lehr_nm_sweep

_time compression 60x (slow processes only: early-phase decay, protein, late phase, CREB)_

## Experiment 5 -- Lehr et al. 2022 NM sweep, reproduction attempt

Reduced network: 400 E / 100 I; 480 s simulated = 8.0 h of slow-process time.

| NM | core-internal z | outgoing z | core w/h0 | outgoing w/h0 | outside-core rate at 8 h recall (Hz) | core rate in learning pulse (Hz) |
|---|---|---|---|---|---|---|
| 0.0 | +0.000 [+0.000, +0.000] (n=10) | +0.000 [+0.000, +0.000] (n=10) | +1.293 [+1.119, +1.467] (n=10) | +1.260 [+1.075, +1.445] (n=10) | +54.412 [-37.225, +146.048] (n=10) | +500.000 [+500.000, +500.000] (n=10) |
| 0.03 | +0.746 [+0.649, +0.842] (n=10) | +0.300 [+0.034, +0.566] (n=10) | +2.155 [+1.836, +2.475] (n=10) | +1.673 [+1.169, +2.176] (n=10) | +120.994 [-17.401, +259.390] (n=10) | +500.000 [+500.000, +500.000] (n=10) |
| 0.06 | +0.875 [+0.798, +0.952] (n=10) | +0.713 [+0.533, +0.893] (n=10) | +2.549 [+2.261, +2.837] (n=10) | +2.361 [+1.952, +2.770] (n=10) | +229.815 [+71.731, +387.899] (n=10) | +500.000 [+500.000, +500.000] (n=10) |
| 0.12 | +0.902 [+0.828, +0.975] (n=10) | +0.878 [+0.787, +0.970] (n=10) | +2.661 [+2.397, +2.925] (n=10) | +2.611 [+2.311, +2.912] (n=10) | +277.196 [+119.517, +434.876] (n=10) | +500.000 [+500.000, +500.000] (n=10) |
| 0.18 | +0.941 [+0.873, +1.008] (n=10) | +0.935 [+0.860, +1.009] (n=10) | +2.765 [+2.495, +3.035] (n=10) | +2.744 [+2.451, +3.038] (n=10) | +359.229 [+212.823, +505.635] (n=10) | +500.000 [+500.000, +500.000] (n=10) |
| 0.24 | +0.919 [+0.844, +0.993] (n=10) | +0.912 [+0.831, +0.993] (n=10) | +2.700 [+2.422, +2.978] (n=10) | +2.680 [+2.383, +2.977] (n=10) | +318.608 [+163.512, +473.703] (n=10) | +500.000 [+500.000, +500.000] (n=10) |

### Pre-registered criteria

- **C1_no_NM_no_consolidation**: PASS
- **C2_core_consolidates_at_low_NM**: PASS
- **C3_outgoing_needs_higher_NM**: PASS
- **C4_outside_activity_rises_with_NM**: PASS

The last column is a check on the STIMULUS, not a result: a core rate at the refractory limit (500 Hz) means the reference's learning-stimulus amplitude, taken literally, saturates the cells. Unverified against the paper's figures.

Spearman rho, outgoing z vs NM: +0.94; outside-core recall activity vs NM: +0.94.

**4/4 criteria pass.** The published qualitative pattern is reproduced at this scale; extensions may build on it.
