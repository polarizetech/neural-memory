# 20260921-013311_population_theta

_time compression 60x (slow processes only: early-phase decay, protein, late phase, CREB)_

## Population signal -- evoked (theta free) vs entrained (theta phase-reset on onsets)

Benchmark: Doelling et al. 2019 (doi:10.1073/pnas.1816414116), note rates (1.0, 1.5, 5.0, 8.0) nps. Published PCM: evoked model 0.245, oscillator model 0.58, MEG 95% CI (0.3, 0.57) (L) / (0.35, 0.59) (R).

### theta `free`
- LFP proxy = RECURRENT + inhibitory currents (afferent current excluded). With the afferent current included the proxy is mostly the input itself: PCM 0.994, latency 6 ms.
- PCM test informative at this latency: **NO -- the latency is too short for evoked and oscillator accounts to predict different PCM; read nothing into the PCM verdict below**
- PCM over rates: +0.997 [+0.997, +0.997] (n=10) -- PCM 0.997 is above the published MEG 95% CI envelope (0.30-0.59) and nearer the published oscillator-model value
- phase lag by rate (rad): {1.0: -0.02, 1.5: -0.05, 5.0: -0.01, 8.0: 0.14}; slope = 4 ms effective latency
- stimulus-LFP coupling (PLV): +1.000 [+1.000, +1.000] (n=40)
- recall ORDERING (Spearman rho): -0.058 [-0.147, +0.030] (n=40); recall r: +0.018 [-0.003, +0.039] (n=40)

### theta `reset`
- LFP proxy = RECURRENT + inhibitory currents (afferent current excluded). With the afferent current included the proxy is mostly the input itself: PCM 0.994, latency 6 ms.
- PCM test informative at this latency: **NO -- the latency is too short for evoked and oscillator accounts to predict different PCM; read nothing into the PCM verdict below**
- PCM over rates: +0.997 [+0.997, +0.997] (n=10) -- PCM 0.997 is above the published MEG 95% CI envelope (0.30-0.59) and nearer the published oscillator-model value
- phase lag by rate (rad): {1.0: -0.02, 1.5: -0.05, 5.0: -0.01, 8.0: 0.14}; slope = 4 ms effective latency
- stimulus-LFP coupling (PLV): +1.000 [+1.000, +1.000] (n=40)
- recall ORDERING (Spearman rho): -0.096 [-0.197, +0.005] (n=40); recall r: +0.021 [-0.002, +0.043] (n=40)

