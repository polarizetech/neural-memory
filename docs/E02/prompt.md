# Prompt for the sim-neural-memory coding agent — open experiment E02

You maintain `polarizetech/sim-neural-memory` (local `~/Sites/sim-neural-memory`; Python package `neurotape`). It is
governed by the KIT Adaptive Preregistration protocols vendored in `.agents/protocols/`: `PREREG_PROTOCOL.md`,
`EXPERIMENT_PR_LOG.md` and `CONVERSATIONS.md`. **Read all three before doing anything.** Where this prompt and a
protocol conflict, stop and say so.

## Background (why E02 exists)

- **E01-stentor-map** is closed with verdict **FAIL** (PR #1, tags `E01-stentor-map-*`). **Do not modify anything in
  `experiments/E01-stentor-map/`.** What it established:
  - The two-pool depletion cascade deepens its decrement when slow recovery is slowed. That was a PASS, but it was
    near-guaranteed by the equations.
  - A treatment-matched control drains to the floor when recovery is frozen. This contradicts Stentor, where untrained
    drug-treated cells keep baseline responsiveness (Rajan et al. 2026, *Curr Biol*, doi 10.1016/j.cub.2026.03.080).
  - No dishabituation occurred. That *matches* Stentor, which does not dishabituate (Rajan & Marshall 2025, *Curr
    Biol*, doi 10.1016/j.cub.2025.05.071).
  - Stimulus specificity was never tested.
- **Steps 1–2 of the habituation model (`docs/habituation/`)** showed two things:
  - Presynaptic depletion generalises to every stimulus that shares its input fibres.
  - A per-synapse, postsynaptically gated depression (`hebb_only`) is stimulus-specific and lasts.
- The motivating mouse study is Tsukano et al. 2026 (*Nat Neurosci*, doi 10.1038/s41593-026-02217-z): top-down
  frontal cortex (OFC) input recruits A1 SST cells to cancel familiar tones, stimulus-specifically, over days.
  **This repository's small networks cannot represent that loop.** E02 tests a *local* learned negative image, of the
  kind described in Drosophila olfactory habituation (Das et al. 2011, doi 10.1073/pnas.1106411108) and Ramaswami 2014
  (doi 10.1016/j.neuron.2014.04.035). It must never be described as modelling OFC.
- A pressure test of the first E02 draft found that most of its predictions passed by construction. The design below
  is the revised one; its reasoning is in the report that accompanies this prompt.

## The question (E02)

**Primary.** Where does synaptic depletion alone (the membrane-physics premise) stop carrying *stimulus-specific*
retention, as a function of input overlap and delay?

**Secondary.** Can two local learned mechanisms be told apart by removing the inhibitory pathway? The two are:

- inhibitory potentiation (a negative image);
- postsynaptically gated excitatory depression (`hebb_only`).

**The premise, stated in PREREG §1:** Arm A's failure region is the reportable finding. Arms B and H are sufficiency
comparators, not the hypothesis. Results are statements about models, never evidence about biology.

## Arms (only these; no other mechanism may be added)

| Arm | Mechanism | Status |
|---|---|---|
| **A** | existing two-pool relay→E depression (`depression.on`, long-term off) | exists at model-v0.1.0 |
| **H** | existing `hebb_only` (anti-Hebbian per-synapse depression; η_hebb 0.0125, as in E01) | exists |
| **B** | A + a **learned, stimulus-specific inhibitory pathway**: an inhibitory population driven by the relay (tonotopic, like E), whose I→E synapses potentiate by a local rule when pre- and postsynaptic activity coincide (a negative image), with a slow decay | **new** |
| **R** | Stentor receptor-inactivation structure (Rajan & Marshall 2025): surface → internalised → recycled or degraded, plus constant synthesis, on the relay→E synapses, with a "synthesis block" manipulation | **new** |
| **0** | plasticity off (no depression, no long-term rule) | exists (`none`) |

Plus **two readout positive controls**, which are not mechanisms:

- a **global-gain decrease** applied across sessions, to show the axis readout can tell global gain from
  stimulus-specific suppression;
- the plasticity-off pairing, which calibrates the paired MDE.

## Stimuli and design (fix every value in PREREG before any run)

- **Exposed input A and unexposed input B, present in every run.** The overlap between their relay footprints is
  graded: **none / partial / full**, defined by a pre-registered overlap metric on the naive relay profiles. Naive
  drive is matched between A and B at each overlap level.
- **Stimulus ≥ 1.5 s**, with pre-registered **onset** and **sustained** analysis windows (for example 0–0.2 s and
  1.0–1.5 s).
- **Sessions.** N presentations per session; K sessions separated by pre-registered gaps, fast-forwarded as the model
  already does. Say "session", never "day".
- **Probes:**
  - B's response after training (the specificity control);
  - retention at pre-registered delays, including Stentor-relevant ones (20, 30, 60 and 90 min) for Arm R.
- **Pathway removal** (the "in-silico muscimol"). In Arm B, set the learned inhibitory pathway's output to zero:
  - **after** training, and
  - **before** training, starting from a **pre-registered non-zero** initial weight.

  Apply the same removal to Arms H and A, which have no such pathway, as the discriminating test.
- **Synthesis block (Arm R):** synthesis rate × {1, 0.25, 0} from training onset, applied to trained *and* untrained
  networks.
- **Session schedule: massed vs spaced at equal presentation count** (Beck & Rankin 1997 — C. elegans long-term habituation needs spaced training). Pre-register what each arm predicts for this contrast.
- **Seeds: 20 per arm × condition**, fixed list. Each seed is a different network and stimulus family, as in E01.

## Predictions and criteria (write them numerically in PREREG §2–4, derived analytically where possible)

For every prediction give: the direction, a numeric threshold, the falsifying result, and whether it is guaranteed
by construction. **Guaranteed predictions are labelled "positive control" and cannot count toward a verdict.**

- **A-map (primary, measurement plus bound).** Specific retention for Arm A over overlap × delay, reported as the
  largest delay and overlap at which A's specific retention exceeds the TOST upper bound.
  - Pre-register the analytic boundary from `habituation/analytic.py` (extended if needed) before the run.
  - Falsifier: the observed boundary lies outside the analytic prediction's pre-registered tolerance.
- **B-vs-H removal (discriminating).**
  - Removing the inhibitory pathway after training reverses B's suppression by at least a pre-registered fraction of
    B's learned component, where "learned component" = B's suppression minus Arm A's suppression under matched
    conditions.
  - The reversal is **specific**: exposed / unexposed reversal ratio ≥ a pre-registered value.
  - The same removal changes H by less than the TOST bound.
  - Falsifier: B does not reverse beyond the bound, or H does.
- **B-naive removal.** With the pre-registered non-zero initial weight, removal in a naive network changes responses
  by less than the TOST bound. Falsifier: a change beyond the bound.
- **R (Stentor constraints).**
  - The synthesis block accelerates the decrement: the half-decrement point is earlier, where half-decrement =
    first n with R_n ≤ R₁ − ½(R₁ − R_last). Report absolute halving too.
  - It prolongs retention at 20–90 min.
  - **The untrained baseline under the block stays within the TOST bound over the whole retention window.**
    Falsifier: the baseline drains.
  - No dishabituation or day-scale claims.
- **Axis readout (measurement).** The angle between the within-session and across-session change vectors (onset and
  sustained windows), per arm, reported against a **per-seed shuffle null** (label-permuted trials).
  - It is a *measurement* unless an analytic expectation is derived before the run.
  - The global-gain positive control must be distinguishable from stimulus-specific suppression, or the readout is
    declared uninformative.
- **Measurement fixes carried from E01:**
  - TOST on the area under the decrement curve, with bounds set from a stated smallest effect of interest;
  - a paired MDE computed from the design's own plasticity-off pairing;
  - an effect under the MDE is **UNINTERPRETABLE**, not FAIL;
  - averaged first responses (mean of a pre-registered first-k) for every decrement ratio.

## Process — follow in this order and stop where told

1. **Model changes first, on their own branch** (PREREG_PROTOCOL §2; EXPERIMENT_PR_LOG §1: model changes go on
   `model/<topic>`, never on the experiment branch).
   - Branch `model/e02-mechanisms` off `main`. Implement **only** Arms B and R, the pathway-removal switch, the
     synthesis-block switch, the global-gain control and the axis readout.
   - Every new switch defaults **off**. Unknown config keys raise.
   - Tests: add tests for each new mechanism, including one asserting each switch-off path is bit-identical to
     model-v0.1.0.
   - **Bit-for-bit:** re-run all 260 habituation runs and E01's 90 runs. Every `runs.json` must be byte-identical to
     its committed copy. Report the test count.
   - Update `CHANGELOG.md`, stating that it invalidates nothing.
   - Merge to `main` with a **merge commit** (never squash), and tag **model-v0.2.0** with `.agents/tools/tag`.
2. **Open E02.**
   - Branch `experiment/E02-local-negative-image` off `main`.
   - Empty start commit, push, then open a draft PR:
     `gh pr create --draft --title "E02-local-negative-image: …"`.
3. **Write, before any run:**
   - `experiments/E02-local-negative-image/PREREG.md` with **all ten sections** of PREREG_PROTOCOL §3;
   - `config.yaml`, naming model-v0.2.0 and the fixed seed list;
   - `ENV.lock`, with hashes;
   - `run.py`, the only entry point, which refuses to run without the `-prereg` tag or if a frozen file or `src/`
     differs from its tag, as E01's does;
   - `analyse.py`, the frozen analysis;
   - `DEVIATIONS.md`, reading "No deviations".

   PREREG must contain:
   - every **new equation and parameter**, tagged **[LIT: doi] / [DERIVED] / [ARBITRARY]** with its source. The
     inhibitory plasticity rule needs a retrieved source, read through the paper library, or it is tagged
     [ARBITRARY];
   - the numeric pass criteria, with the falsifier for each prediction;
   - the TOST bounds and the SESOI they come from;
   - the seed counts, and the MDEs with their derivation;
   - the analytic predictions (with the code that produced them committed);
   - **every decision this prompt leaves open, listed in §9 and decided there**: overlap metric and levels, delays,
     session structure, window edges, initial weight, first-k, SESOI.
4. **Each stage's control runs before that stage's result is reported:**
   - the plasticity-off pairing, before the MDE is used;
   - the global-gain control, before the axis readout is interpreted;
   - the untrained-block baseline, before Arm R's retention is interpreted.
5. **Tag** `E02-local-negative-image-prereg` with `.agents/tools/tag` (it posts the receipt to the PR). **STOP and
   show the operator PREREG.md. Run nothing until approved.**
6. After approval:
   - run;
   - write `RESULTS.md` per PREREG_PROTOCOL §6, with the pre-registered value beside each observed one, "patterns the
     model failed to reproduce", and "what only worked because it was tuned";
   - put anything post hoc under `exploratory/`;
   - tag `-run` and then `-closed`, and mark the PR ready.

## Report back each time you stop

- Commits, with hashes.
- Tags and receipt links.
- Test count, and bit-for-bit status for every earlier experiment.
- A verdict table (predicted vs observed, per criterion).
- Deviations logged, with `outcome_known` set honestly.
- Every open decision, **stated before the run it affects**.

## Forbidden

- Tuning any parameter so that a criterion passes.
- Adding or changing criteria after seeing output. Changes go in DEVIATIONS.md, and after the output is seen they
  cannot turn a FAIL into a PASS.
- Editing PREREG.md after `-prereg`.
- Bare `git tag`.
- Squash merges.
- Modifying E01.
- Mechanisms not listed above.
- Describing any result as evidence about mouse cortex, OFC, Stentor, or biology generally. Results are about these
  models.
