# E01-stentor-map — Deviations

Schema: PREREG_PROTOCOL.md §5 (Willroth & Atherton 2024).

| # | Date | Stage/section | Type | Original text | Change | Reason | Outcome known? | Effect on interpretation | Commit |
|---|------|---------------|------|---------------|--------|--------|----------------|--------------------------|--------|

| 1 | 2026-09-24 | §3 SR3 criteria (analyse.py verdict) | criterion | "95 % t-CI upper bound < 0 for **both** inserts" → PASS, else FAIL | A minimum detectable effect (MDE) is added. MDE = t(0.975, 9) · SD / √10, SD = between-seed SD of the presentation-9/presentation-8 response ratio in EXISTING runs (1.5 s stimulus, ISI 3 s): `std` 0.0350 (hab_memory, SD 0.0490); `hebb_only` 0.0125 (sweep_eta_x0.25, SD 0.0174); `none` 0.0147. Rule: if \|mean effect\| < that arm's MDE the SR3 verdict is UNINTERPRETABLE, not FAIL (and not PASS); otherwise §3 applies unchanged. analyse.py stays frozen; RESULTS.md applies this rule on top of its verdict | operator, before any run: the analytic effect for `std` (−0.21 %, −0.33 %) is ~10× below the detectable size, so a FAIL would report an undetectable effect as a negative | no | a small effect can no longer be scored as a failed prediction. Caveats: the SD is a proxy (1.5 s not 0.2 s stimulus; consecutive presentations, not paired series with shared noise), so the MDE is conservative for the paired SR3 design. Predicted SR3-`std` verdict under this rule: UNINTERPRETABLE | (this commit; tag E01-stentor-map-interim-1) |
