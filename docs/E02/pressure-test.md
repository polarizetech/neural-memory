# E02 design — pressure test (2026-09-24)

**Read depth.** [FT] full text read this session · [AB] abstract or citation snippets only · [BG] background
knowledge, not retrieved. Confidence is given as High / Medium / Low with a rough percentage.

**Sources and how they were read.** Everything came through the `kit-scientific-research-rag` MCP gateway
(paper library, `dd874b9`) plus scite metadata for closed papers.

- **[FT], read this session:**
  - Tsukano et al. 2026 (*Nat Neurosci*, doi 10.1038/s41593-026-02217-z): the whole text, 95,875 characters.
  - Rajan & Marshall 2025 (*Curr Biol*, 10.1016/j.cub.2025.05.071).
  - Rajan et al. 2026 (*Curr Biol*, 10.1016/j.cub.2026.03.080).
  - Requarth & Sawtell 2014 (*Neuron*, 10.1016/j.neuron.2014.03.025): introduction.
  - Hertäg & Sprekeler 2020 (*eLife*, 10.7554/eLife.57541): introduction and model.
  - Esdin et al. 2010 (*Front Behav Neurosci*, 10.3389/fnbeh.2010.00181): introduction and methods.
  - Smart et al. 2024 (*PNAS*, 10.1073/pnas.2409330121): introduction.
  - Eckert et al. 2024 (*Curr Biol*, 10.1016/j.cub.2024.10.041): summary.
  - Malmierca et al. 2009 (*J Neurosci*, 10.1523/JNEUROSCI.4153-08.2009): introduction and methods.
- **[AB] only, because no open-access full text was obtainable:**
  - Ezzeddine & Glanzman 2003 (10.1523/JNEUROSCI.23-29-09585.2003);
  - Das et al. 2011 (10.1073/pnas.1106411108);
  - Ramaswami 2014 (10.1016/j.neuron.2014.04.035);
  - Anderson et al. 2009 (10.1523/JNEUROSCI.0793-09.2009);
  - Bell et al. 1997 (10.1038/387278a0).

**Tool limits hit, stated rather than hidden.**
- The gateway's `rag__retrieve_evidence` index held 3 unrelated papers, so it returned irrelevant passages and never
  triggered its open-access fallback. Evidence below comes from direct full-text reads, not from that index.
  `rag__check_citations` / `rag__save_report` could therefore not validate these citations.
- The pipeline's own library store is separate and in-memory on this machine (no Spaces credentials), so
  `research_pipeline index` saw 0 papers. The pipeline's online `ask` runs were started separately; see the end.

---

## Step 1 — P1–P7 checked against the paper [FT]

| # | Verdict | What the paper actually says (figure) | Confidence |
|---|---|---|---|
| P1 | **Mostly correct, one overreach, one missing null** | Fig. 1i–m: Mode_within and Mode_across are "nearly orthogonal (78.2 degrees)". Within-day habituation "markedly attenuated sound onset responses"; across-day was "greater during the sustained phase". **"Bottom-up" for within-day is the authors' hedge** ("may be driven by faster, bottom-up mechanisms"), not a result. **No null for the angle is reported in the main text.** It is one pooled estimate over 2,398 cells from 20 mice, computed from a chosen metric (per-ROI min–max normalisation; summed 0.5–1.5 s and 4–5 s windows; Mode_within = trials 1–10 → 91–100 averaged over days; Mode_across = day 5 − day 1). Random vectors in ~2,400 dimensions have cos ≈ N(0, 1/√N) ≈ ±0.02, i.e. ~88.8° ± 1.2° [BG, geometry]. **78.2° (cos ≈ 0.20) is therefore *more aligned* than chance, not evidence of independence.** | High 85 % |
| P2 | **Misstated** | The paper does **not** show that fatigue or homosynaptic depression is insufficient. Its *Introduction* says internal-model-free mechanisms ("sensory receptor fatigue, homosynaptic depression, and the short-term dynamics of inhibitory neuron firing") "fail to fully account for" persistence over weeks, multi-channel stimuli, context dependence and disruption by anaesthesia, citing earlier work. The only in-paper evidence against subcortical inheritance is a citation to their own earlier study (across-day plasticity in L2/3, not in L4). | High 90 % |
| P3 | **Correct values; one qualification** | Fig. 2j–s. Muscimol after 5 days: change index 0.31 ± 0.04 (P = 2.0 × 10⁻¹³; 7 mice, 296 excited neurons). PBS: 0.034 ± 0.094 (P = 0.76, **3 mice**). Naive: −0.002 ± 0.017 (P = 0.82, 4 mice); naive PBS −0.037 ± 0.015 (P = 0.15, 6 mice). **Qualification:** the naive infusion was given *after 100 trials on day 1* and compared blocks 6–8 against 2–4, so it is "no effect on day-1 responses", not "before any exposure". Concentration is 2.5 mg ml⁻¹ in the Results and 2.5–5 mg ml⁻¹ in the Methods. Replicated with optogenetic OFC silencing (Ext. Data Fig. 8): no effect on day 0, and on day 6 a >10× larger effect on tone A than tone B. | High 90 % |
| P4 | **Correct; limited in scope** | Fig. 5. Axons: tone A 0.55 ± 0.14 (P = 0.0042), tone B 0.06 ± 0.17 (P = 0.71); 11 mice, 161 boutons (22 and 26 excited). Somata: tone A −0.66 ± 0.04 (P = 8.8 × 10⁻²²), tone B 0.06 ± 0.05 (P = 0.17); **4 mice**, 551 neurons. **Limits:** one frequency separation (one octave, flanking best frequency), so there is no generalisation gradient; tone B had only 10 trials on days 0 and 6. | High 85 % |
| P5 | **Supported, correlational** | Fig. 1n–q. Pupil itself habituated across days. Day-5 responses were smaller than day-1 in every pupil-diameter bin (10 mice, 977 cells, two-way ANOVA P = 2.0 × 10⁻³⁰). "Independent" means *not explained by pupil level*; arousal was not manipulated. | Medium-High 75 % |
| P6 | **Partly misstated** | Rabies tracing shows OFCvl input to **both** SST and VIP (Fig. 2e–h). "OFC→SST" as the operative route is inferred from muscimol effects (SST −0.50 ± 0.06, VIP +0.55 ± 0.10, PV +0.18 ± 0.06; Fig. 3) and the Fig. 6h schematic. **SST–VIP mutual inhibition is cited (refs 54–56), not measured.** Activating A1-projecting OFC cells suppresses A1 (modulation index −0.23 ± 0.06, 6 mice; Fig. 4o), but the cell-type route is not shown. NMDAR knockout: A1-wide (4 vs 5 mice) and SST (5 vs 6) attenuate habituation; VIP (4 vs 5) does not (Fig. 6g) — correct. **Implication for modelling:** local A1 NMDAR-dependent plasticity also contributes, so the mouse mechanism is *top-down plus local plasticity*, not top-down alone. | High for the knockouts (90 %); Medium for "OFC→SST" (60 %) |
| P7 | **Mostly correct, with additions** | Post-habituation PBS n = 3 (naive-arm PBS n = 6). Statistics are Wilcoxon tests over **neurons pooled across mice**, a pseudoreplication risk. "The experiments were not performed blind", but ROI segmentation and spike sorting were blind to trial type. Sample sizes were not predetermined. Muscimol spread is not quantified in the main text or Methods (Extended Data not read, so this is [FT] for the main text only). Passive tones, head-fixed. **Added:** one frequency per mouse; mixed 5/7/9 s tone durations; knockout groups of 4–6 mice. | High 85 % |

**Correction to the prompt's own context.**
- **Stentor does not dishabituate** (Rajan & Marshall 2025 [FT]: "Dishabituation does not occur in Stentor"), and
  "Long term habituation has not been observed in Stentor" [FT]. So E01's "no dishabituation in any arm" *matches*
  the organism. It was listed as a failure only because SR3 was framed as dishabituation vs deepening.
- The Rajan et al. 2026 result E01 targeted is confirmed [FT]: puromycin and cycloheximide accelerated habituation
  and improved retention at 20–90 min after 12 h of training.
- It carries a constraint E01 violated: **untrained drug-treated cells contracted at control levels after 3–13.5 h
  of drug.** The block does not drain baseline responsiveness. E01's frozen and ×0.1 controls drained, so that result
  is a model–organism mismatch, not only a design flaw.

## Step 2 — Mapping validity

| Design item | Justified by the mouse (or Stentor) finding? | Confidence |
|---|---|---|
| **Scale** | **No, for anything OFC-specific.** A 200-cell tonotopic network cannot contain a frontal predictor, a long-range loop, or day-scale consolidation. What it *can* contain is a **local** learned inhibitory negative image of the kind in Drosophila olfactory habituation (Das 2011 [AB]), the Ramaswami 2014 model [AB] and Hertäg & Sprekeler 2020 [FT]. E02 must say it tests a *local* negative image, not "predictive filtering by OFC". | High 85 % |
| **D1** (Arm A vs Arm B) | Arm A is justified as the premise test. Arm B's justification comes from invertebrate and local-circuit evidence, **not** from Tsukano, whose predictor is extrinsic to A1. | Medium-High 75 % |
| **Must a negative image have a cortical predictor?** | **No, but it needs a predictor *signal*.** In cerebellum-like circuits negative images form by local anti-Hebbian plasticity, *given* a separate predictive input (corollary discharge; Bell 1997 [AB], Requarth & Sawtell 2014 [FT]). In habituation, Tsukano argue the stimulus onset is the cue predicting its continuation [FT]. So a local learned inhibitory synapse can stand in; to reproduce the *sustained-phase* ramp it needs an onset-driven, delayed input. | Medium 65 % |
| **D2** (unexposed input) | **Strongly justified** by P4. It also answers E01's biggest gap: steps 1–2 showed that spectral overlap, not the mechanism, decided specificity for presynaptic depletion. | High 85 % |
| **D3** (in-silico muscimol) | **Justified as an analogue, not as a test** (see Step 4). Muscimol removes the *source* of the prediction; deleting Arm B's inhibitory synapses removes the *stored image itself*. Reversal then follows by construction. | High 85 % |
| **D4** (inactivation arm) | Justified by Stentor: it is Rajan & Marshall's published structure (surface → internalised → recycled or degraded, plus synthesis) [FT]. **But it cannot speak to day-scale memory:** Stentor retention was measured over ~90 min and long-term habituation has not been seen. | High 80 % |
| **D5** (axis angle) | Justified only with **(i) a shuffle null**, since chance is ~90° ± ~4° for 200 cells, and **(ii) a stimulus with a sustained phase**. E01's 0.2 s has none; Tsukano used 5–9 s. Without a derived prediction it is a measurement, not a test. | High 85 % |
| **P5** (arousal) | **Not relevant to the model's mechanism**: NM/salience is off, so there is no arousal channel. No covariate is needed. A **global-gain positive control** is still worth adding, to show the readout can tell global gain from stimulus-specific suppression. | Medium 65 % |

## Step 3 — Competing evidence

| Evidence | Read depth | Bears on | Supports / contradicts / neutral |
|---|---|---|---|
| Aplysia long-lasting (1–6 h) habituation in a reduced preparation needs protein synthesis, PP1/PP2A and **postsynaptic** NMDA/AMPA receptors; "homosynaptic depression … does not play a significant role"; site-specific (Ezzeddine & Glanzman 2003) | [AB] | D1, P2 | **Contradicts** "long-term habituation needs top-down input" (a ganglion suffices). **Supports** P2's spirit (presynaptic depletion is insufficient for the long form) and a *postsynaptic* local mechanism. Note the opposite protein-synthesis dependence to Stentor. |
| Aplysia long-term habituation lasts weeks; long-term sensorimotor depression plus presynaptic retraction; needs transcription (Esdin et al. 2010) | [FT] | D1 | **Contradicts** top-down necessity; neutral on inhibition. |
| Drosophila olfactory short- and long-term habituation (days) from potentiation of **local GABAergic** interneuron inhibition, odour-selective via PN NMDA/GABA_A (Das et al. 2011) | [AB] | D1 Arm B, D2 | **Supports** a local, stimulus-specific inhibitory negative image with no cortex. |
| Negative-image model: habituation from "target-specific scaling of inhibitory inputs onto active excitatory neurons" (Ramaswami 2014) | [AB] | D1 Arm B | **Supports** Arm B as a *local* mechanism. |
| Cerebellum-like negative images from anti-Hebbian, timing-dependent parallel-fibre depression (Bell et al. 1997); learned from corollary discharge (Requarth & Sawtell 2014) | [AB] / [FT] | D1, D5 | **Complicates**: local learning works, but requires a predictive input channel distinct from the sensory one. |
| Stentor: receptor-inactivation model; no dishabituation; no long-term habituation; force- and modality-specific; strong stimuli deplete a hidden variable (Rajan & Marshall 2025) | [FT] | D4, SR3 framing | **Supports** D4 as a reproduction. **Contradicts** Stentor being a model for day-scale or dishabituation predictions. |
| Stentor: protein-synthesis inhibitors *accelerate* habituation and prolong retention (to 90 min); untrained baseline unchanged; memory survives division (Rajan et al. 2026) | [FT] | D4, D6 retention control | **Supports** D4's prediction, and gives a **falsifier E01 failed**: the untrained baseline must not drain. |
| Minimal single-cell motifs (negative feedback, incoherent feedforward) reproduce all *single-stimulus* hallmarks; linear systems do not habituate (Eckert et al. 2024; Smart et al. 2024) | [FT] | Step 4 | **Complicates**: many mechanisms pass single-stimulus hallmarks, so only multi-stimulus tests (specificity, pathway removal) can discriminate. |
| Local homeostatic inhibitory plasticity learns prediction-error circuits in a PC/PV/SST/VIP model, and its variants have distinct optogenetic fingerprints (Hertäg & Sprekeler 2020) | [FT] | D1 Arm B, D3 | **Supports** a learned local inhibitory pathway, plus removal experiments with a *discriminating* signature. |
| Stimulus-specific adaptation in the inferior colliculus (urethane-anaesthetised rat; Malmierca 2009) and the auditory thalamus (anaesthetised mouse, ISI 0.4–0.8 s, mainly non-lemniscal; Anderson 2009) | [FT] / [AB] | P1 "within-day = bottom-up" | **Supports** fast specific adaptation without cortex. Neutral on the day-scale component. |
| Tsukano: A1 and SST NMDAR knockout attenuates habituation | [FT] | D1 | **Complicates** "top-down only": local plasticity is part of the mouse mechanism. |

## Step 4 — Falsifiability audit

| Prediction | (a) Falsifying result | (b) Can the design produce it, or does it pass by construction? | (c) Seeds / effect size |
|---|---|---|---|
| A1: Arm A gives a fast decrement | no decrement | **By construction.** Depletion *is* a decrement. A positive control, not a test. | — |
| A2: Arm A fails stimulus-specific retention | Arm A retains specifically | **Decided by a parameter.** With non-overlapping inputs, per-fibre depletion is specific at short delays automatically. At delays ≫ τ_slow (20 s) it is gone automatically. **Only testable across graded overlap and delay**, with the boundary predicted analytically in advance. | Paired MDE from the design's own plasticity-off pairing. E01's hebb_only recognition had SD ≈ 0.017 at n = 10, so 80 % power for 0.02 needs n ≈ 7 → use 20. |
| B1: Arm B retains specifically | Arm B does not, or generalises | **Near-guaranteed** with input-specific Hebbian inhibitory plasticity and no overlap. Informative only under overlap (a generalisation gradient) and interference. | Same. |
| B2: removing Arm B's pathway after learning reverses habituation | no reversal | **By construction** if removal deletes the only storage. Informative only if the prediction is *quantitative* (fraction reversed relative to Arm A's separately measured residual) and *specific* (exposed ≫ unexposed, as in Tsukano's Ext. Data Fig. 8). | TOST on the reversal fraction. |
| B3: removal in a naive network has no effect | a naive effect | **By construction** if initial weights are ≈ 0. Informative only if the initial weight is a pre-registered non-zero value, with a TOST bound. | TOST ±SESOI; ~12–20 seeds at SD 0.017 and bound 0.02. |
| D4: synthesis block → faster decrement *and* longer retention | slower decrement, or shorter retention | **Partly structural** (less supply means faster depletion). The **real test is the Stentor constraint**: the untrained baseline under the block must stay within a bound over the retention window. E01's structure failed exactly this. | TOST on the untrained baseline change. |
| D5: within- vs across-session angle | no prediction derived | **Neither — it is a measurement** until an analytic expectation per arm exists. It needs a per-seed shuffle null, and a sustained-phase stimulus. | Report the angle minus its null, with a CI. |

**Analytically guaranteed (flag them): A1; A2 at the extreme delays and overlaps; B1 without overlap; B2; B3 with zero
initial weight.** These are E02's versions of E01's SR1-`std`.

## Step 5 — Premise check

Adding a learned inhibitory pathway **does abandon the premise** (what membrane physics gives for free) *for that
arm*. That is acceptable only if the framing makes the premise the result:

- **Primary question (Arm A):** *Where exactly does depletion stop carrying stimulus-specific retention?* Answer with
  a pre-registered map of retention against input overlap × delay, with an analytic boundary. **Arm A's failure region
  is the headline finding**, reported as a quantity: the largest delay and overlap at which depletion alone gives
  retention above the TOST bound.
- **Comparators, labelled as sufficiency checks rather than tests:**
  - Arm B (local learned inhibition);
  - Arm H (the existing `hebb_only`: postsynaptically gated excitatory depression, which already recognised in
    steps 1–2 and resembles Aplysia's postsynaptic long-lasting habituation).
- **The one genuinely discriminating comparison:** removing the *inhibitory* pathway should reverse B but **not** H,
  and a strong novel stimulus can disinhibit B but not H. This distinguishes the two local memory types
  (inhibitory potentiation vs excitatory depression) that Ramaswami 2014 contrasts [AB].

## Step 6 — Revisions

| # | Change | Reason | Confidence |
|---|---|---|---|
| R1 | Reframe Arm B as a **local** learned inhibitory negative image. Drop "OFC analogue" language everywhere. | Scale (Step 2); Tsukano's predictor is extrinsic. | High 85 % |
| R2 | **Add Arm H** (existing `hebb_only`, unchanged), and make pathway removal discriminate B from H. | It turns a by-construction reversal into a test between two mechanisms. | Medium-High 75 % |
| R3 | D2 becomes **graded input overlap** (none / partial / full), with naive drive matched per input. | Specificity is decided by overlap (steps 1–2); P4 tested one separation only. | High 85 % |
| R4 | D3 predictions become **quantitative and specific**: reversal fraction vs Arm A's residual, and an exposed/unexposed reversal ratio. The pathway's initial weight is pre-registered, and the qualitative versions are labelled positive controls. | Step 4 (B2, B3 are guaranteed). | High 85 % |
| R5 | D4 = Rajan & Marshall receptor-inactivation structure, run as its own arm, with the Stentor constraints. **Falsifier:** the untrained baseline drains under the block. Retention is read at 20, 30, 60 and 90 min. No dishabituation and no day-scale claims. | Rajan et al. 2026 [FT]; E01's failure mode. | High 80 % |
| R6 | D5 compares against a **per-seed shuffle null**. Stimulus ≥ 1.5 s with a defined sustained window. Add a **global-gain positive control** for the readout. It is a measurement unless an analytic prediction is derived before the run. | Geometry; P1 has no null; P5. | High 85 % |
| R7 | Define "session" and "across-session" in model time (N presentations; gaps fast-forwarded). **Never "day".** | The model has no consolidation or sleep. | Medium-High 75 % |
| R8 | D6: TOST bounds from a SESOI set before the run; **20 seeds per arm**; paired MDE from the design's own plasticity-off pairing; retention control **treatment-matched with a baseline-stability check**. | E01 lessons; power from E01 variance. | High 85 % |
| R9 | Drop "Stentor dishabituation" as a test (Stentor shows none). Keep a strong-novel-stimulus probe **only** as the B-vs-H discriminator. | Rajan & Marshall 2025 [FT]. | Medium 65 % |
| R10 | No arousal covariate (NM stays off). Say so in PREREG §1. | P5 relevance. | Medium 65 % |
| R11 | The plasticity rule for Arm B needs a retrieved source before tagging. The obvious candidate, Vogels et al. 2011's inhibitory STDP, is **[BG] here and must be fetched and read** or tagged [ARBITRARY]. | Protocol: every equation is tagged. | High 80 % |

## Step 7 — the E02 prompt

See `E02-prompt.md`, written to be self-contained.

## Devil's advocate

The strongest case against running E02 as designed: most of its predictions are properties of the equations, not of
anything that can surprise us.

- Arm A must decrement and must forget by τ_slow.
- Arm B must retain specifically when its inputs do not overlap, and must "reverse" when its only storage is deleted.
- The Tsukano mapping cannot be carried at this scale. The Stentor and mouse phenomena differ in organism, timescale
  (minutes vs days) and mechanism (receptor inactivation vs top-down SST recruitment).
- The two questions with real uncertainty could be answered with a far smaller experiment, much of it analytic:
  1. the overlap × delay boundary for depletion;
  2. whether pathway removal separates inhibitory potentiation from excitatory depression.

Without R2–R4, E02 risks being preregistration theatre: a stack of PASSes that are true by construction, dressed in
the language of a mouse paper they cannot test.

---

## Addendum — cross-check by the kit's own research pipeline

`research_pipeline ask`, 4 questions, qwen3:4b as both writer and verifier. Run folders are
`kit-scientific-research-rag/runs/2026-09-24T22*` and `…T23*`.

| Question | Claims kept | Agrees with this report | New or different |
|---|---|---|---|
| Long-term habituation without top-down input? | 2 / 7 | "Long term habituation has not been observed in Stentor" (Rajan & Marshall 2025). Its verifier **rejected a drafted claim that it has** (marked "contradicted"). "Neural circuits … are not required" (Smart 2024). | Aplysia and Drosophila: *insufficient evidence*; it could not obtain open-access copies (this report used their abstracts). |
| Local learned inhibition as a negative image? | 1 / 16 | — (every sub-question insufficient) | **Flags a disagreement** between Chaloner et al. 2022 (doi 10.3389/fncel.2022.840057) and Chen et al. 2026 (doi 10.1016/j.celrep.2026.117306) on inhibitory-plasticity cancellation. **Neither was read here.** Surfaces **Beck & Rankin 1997** (doi 10.3758/bf03209851): *C. elegans* long-term habituation comes from **distributed training at long ISIs, not massed or short-ISI training**. |
| SSA in the inferior colliculus and thalamus? | 11 / 14 | SSA in IC and MGB, mainly non-lemniscal (Malmierca 2009; Antunes 2010). A1 SSA runs on "hundreds of milliseconds to tens of seconds". | **IC SSA increased during cortical cooling** (Ayala 2013, citing a figure). Cortical neurons do not adapt at ISIs > 2 s (Ulanovsky 2003, via Ayala 2013). **Chaloner et al. 2022: "multiple mechanistically distinct timescales of neocortical plasticity during habituation"**, directly relevant to P1. **Verifier error:** one kept claim expands SSA as "synaptic strength adaptation", which is wrong. |
| Stentor mechanism; protein-synthesis or phosphatase block? | 4 / 10 | Receptor inactivation; puromycin and cycloheximide accelerate habituation and prolong retention (Rajan 2026). | **Verifier error:** it *removed* the claim "impairing protein synthesis accelerates habituation and prolongs memory" as "partially supported", although the quoted passage states exactly that. Phosphatase: insufficient; this report's [FT] read found orthovanadate impaired habituation at marginal significance. **New source:** a 2026 Stentor genome and time-resolved transcriptomics preprint linking cyclic-nucleotide-dependent kinase signalling to habituation (doi 10.64898/2026.07.23.740246), **not read**. |

**What this changes in the design.**

- **R12 (new): the session schedule is a design variable, not a free parameter.**
  - Beck & Rankin 1997: in *C. elegans*, long-term habituation needs **spaced** training.
  - Ezzeddine & Glanzman 2003 ([AB]) used "repeated, spaced blocks".
  - So E02 should pre-register **massed vs spaced sessions at equal presentation count**. The mechanisms predict
    different things there: depletion favours massed; a slow learned pathway need not.
  - Confidence: Medium 60 % (read through a 4B pipeline passage; the paper itself not read here).
- **Timescales:** Chaloner et al. 2022 is a second source (beside Tsukano) for multiple distinct habituation
  timescales in neocortex. Read it before E02 cites P1.
- **The IC cortical-cooling result** supports within-session SSA being bottom-up and not inherited from cortex. It
  does not bear on the day-scale component.

**On the tool itself:**
- Its verifier over-rejects (question 4) and under-checks (question 3's mislabelled acronym).
- It shares the writer's model, which it warns about itself (set `PIPELINE_VERIFIER_MODEL` to another family).
- It lacks copies of the key Aplysia and Drosophila papers.
- Treat it as a source-finder here, not an arbiter.
