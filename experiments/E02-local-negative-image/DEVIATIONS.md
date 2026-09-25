# E02-local-negative-image — Deviations

Schema: PREREG_PROTOCOL.md §5 (Willroth & Atherton 2024).

| # | Date | Stage/section | Type | Original text | Change | Reason | Outcome known? | Effect on interpretation | Commit |
|---|------|---------------|------|---------------|--------|--------|----------------|--------------------------|--------|
| 1 | 2026-09-24 | §3 MDE | analysis | "The design MDE is the largest of those cells" (computed from arm Z's paired SR) | Z's trained and control networks are identical (no plasticity), so every paired Z difference is exactly 0 and the design MDE is 0. analyse.py's verdicts are reported as frozen; RESULTS.md adds each criterion's OWN MDE, (t + t)·sd/√n from that criterion's own paired values, beside it | the preregistered MDE is degenerate by construction; this was not foreseen | yes (seen in analyse.py's output) | none on verdicts: every criterion that came out FAIL has its own MDE ≤ 0.035 (P2b; P4 ≤ 0.014), below SESOI, so each FAIL would still be FAIL. The rule can only move FAIL to UNINTERPRETABLE and here moves nothing | (this commit) |
| 2 | 2026-09-24 | §6 exclusions | exclusion | "A failed job is kept in runs.json with its error, listed in RESULTS, and excluded from means" | applied as written to 10 jobs, all Arm B seed 0 (2 main, 8 sensitivity). Cause: a model-v0.2.0 bug -- a plastic FF pathway receiving an FF spike during the 3 s settle, before alpha exists, used a fixed-weight matrix that is None for plastic configs. Not fixed in this experiment (src/ is frozen to model-v0.2.0) | a model bug, found by the run | no (the rule was applied as preregistered, before any analysis) | B's comparisons use 19 seeds; the other 19 B seeds never reached the crash path, so their runs are unaffected | (this commit) |

## Unregistered steps

Steps taken before the -prereg tag that shaped the design. None touched an on-list seed; details in PREREG §8 (U1–U6).

| # | Date | Step | Seeds | Outcome seen? | What it changed |
|---|------|------|-------|---------------|-----------------|
| U1 | 2026-09-24 | FF operating-point scan | 901–902 | naive responses only | w_rf 0.6, w_fe 0.3 |
| U2 | 2026-09-24 | iSTDP engagement scan | 901–902 | synaptic G only | eta 0.015 |
| U3 | 2026-09-24 | "silence drift" diagnosis, reverted | 901–902 | G only | nothing |
| U4 | 2026-09-24 | receptor steady-state / fast-forward check | 901 | pools only | two release-convention bugs fixed in model code |
| U5 | 2026-09-24 | predict.py | 900–909 | analytic efficacy | "none" = lowest of 20 draws; partial band report-only |
| U6 | 2026-09-24 | run.py smoke test | 900 | run status only | nothing |
