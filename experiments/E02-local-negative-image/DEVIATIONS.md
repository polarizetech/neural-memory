# E02-local-negative-image — Deviations

Schema: PREREG_PROTOCOL.md §5 (Willroth & Atherton 2024).

No deviations.

| # | Date | Stage/section | Type | Original text | Change | Reason | Outcome known? | Effect on interpretation | Commit |
|---|------|---------------|------|---------------|--------|--------|----------------|--------------------------|--------|

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
