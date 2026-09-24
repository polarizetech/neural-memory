# E02 — how the research was used (2026-09-24)

This file sits beside two others:

- [`pressure-test.md`](pressure-test.md) — the pressure test of the first E02 draft.
- [`prompt.md`](prompt.md) — the revised E02 prompt that came out of it.

Both were produced by running the operator's pressure-test prompt through `kit-scientific-research-rag` (`dd874b9`)
and by reading the papers directly. This file records four things:

1. which findings E02 **follows**;
2. which parts of the research were **wrong or missing**, and how each was handled;
3. what the sources read *after* the pressure test changed;
4. where E02 **departs from the prompt**, and why.

**Read depth tags:** [FT] full text read · [AB] abstract only · [BG] background knowledge, not retrieved.

## 1. Sources read after the pressure test (closing its "not read" list)

| Source | How read | What it changes for E02 |
|---|---|---|
| Rajan & Marshall 2025, *Curr Biol*, 10.1016/j.cub.2025.05.071 — **Methods** | [FT], reread | See the rows below. |
| ↳ published parameters | | The receptor-inactivation model's parameters: k_int 0.1, k_recycle 0.1, k_synth 0.7, k_deg 0.02, k_des 0.005, plus a hard response threshold. Arm R takes the recycling, degradation and destruction rates from here. |
| ↳ time unit | | The paper gives no unit. Stimuli were one per minute, so E02 reads the rates **per minute**. This is flagged as an assumption. |
| ↳ basal degradation | | The model has **basal degradation of *surface* receptors** (k_deg). Under a full synthesis block, **its own untrained surface pool decays** (τ = 50 min on the per-minute reading). Stentor's untrained baseline survives in their account only because the output is a **hard threshold**: a cell far above threshold keeps contracting while its receptors drain. That output nonlinearity is the load-bearing part of the Stentor constraint, and E02's prediction for Arm R is built on it (PREREG §2). |
| ↳ typo | | Their eq. 2 prints `−(krecycle − kdeg + kdes)`. The text says both pools degrade at k_deg, so E02 uses `+kdeg` and records the reading. |
| Miao et al. 2026 preprint, Stentor genome + time-resolved transcriptomics, 10.64898/2026.07.23.740246 | [AB] + introduction and discussion excerpts via scite | Habituation comes with a **sustained up-regulation** of a PKG / Ca²⁺-channel / PP2A module, which the authors call LTD-pathway components. It adds nothing that a two-pool receptor model can test. It is noted, and no arm is built on it. |
| Beck & Rankin 1997, *Anim Learn Behav*, 10.3758/bf03209851 | [FT] | In *C. elegans*, long-term (24 h) habituation followed **distributed** training (3 × 20 stimuli with **1 h rests**, 60 s ISI) and **not massed** training (60 in a row). Short-term habituation was indistinguishable between the two, possibly a floor effect. E02's massed-versus-spaced contrast copies the **structure** (equal count; 1 h rests; blocks of 20). The ISI is not copied: 60 s is not affordable in direct simulation. |
| Chaloner & Cooke 2022, *Front Cell Neurosci*, 10.3389/fncel.2022.840057 | [FT] | Mouse V1: **within-session decrement and across-days potentiation (SRP) run in opposite directions in the same animals.** Both need NMDA receptors in V1. PV+ inactivation splits fast adaptation into two components, and the interaction between familiarity and adaptation needs PV+ cells. This supports a **local, inhibition-involving** familiarity mechanism (Arm B's premise) and a **postsynaptic**, NMDAR-dependent short-term decrement. It argues against pure presynaptic depletion in cortex (Arm A). It also warns that "across-session change" need not be a *decrement*, so the axis readout is reported as an angle and a sign, never as "more habituation". |
| Chen & Rieke 2026, *Cell Rep*, 10.1016/j.celrep.2026.117306 | [FT], results skimmed | This is retina: presynaptic inhibition relieving synaptic depression. It is **not** a habituation or negative-image source. The pipeline surfaced it on topic similarity. Not used. |
| Vogels et al. 2011, *Science*, 10.1126/science.1211095 | [AB] only (full text closed; erratum noted) | The source for Arm B's rule, inhibitory STDP that drives each postsynaptic cell toward a target rate. The equation is taken from **[BG]** (the standard published form); the abstract confirms the claim that the rule "balances excitation and inhibition" and makes memories "indiscernible from the background state, but … re-activated by external stimuli". The rule's parameters are therefore tagged [BG]/[ARBITRARY], not [LIT]. |

## 2. What the research got right, and how E02 follows it

1. **E01's untrained-baseline failure is a real model–organism mismatch** (Rajan et al. 2026 [FT]). E02 makes the
   untrained baseline under the synthesis block a **pre-registered criterion with a falsifier** (R-base), rather than a
   side observation.
2. **Stentor does not dishabituate and shows no long-term habituation** (Rajan & Marshall 2025 [FT]). E02 has no
   dishabituation test for Arm R and makes no day-scale claim. Retention for R is read at 20, 30, 60 and 90 min only.
3. **The 78.2° angle in Tsukano et al. 2026 has no null, and it is *more* aligned than chance in ~2,400 dimensions.**
   E02's axis readout is always reported against a per-seed shuffle null. It carries a global-gain positive control,
   and it is a measurement, not a pass criterion.
4. **Local negative-image evidence exists** (Das 2011 [AB], Ramaswami 2014 [AB], Bell 1997 [AB],
   Requarth & Sawtell 2014 [FT], Hertäg & Sprekeler 2020 [FT]).
   - Arm B is a *local* learned inhibitory pathway.
   - It is never described as OFC. The mouse loop is top-down plus local plasticity (Tsukano Fig. 6g, [FT]), and
     these networks cannot represent it.
5. **Aplysia long-lasting habituation is postsynaptic and needs protein synthesis** (Ezzeddine & Glanzman 2003
   [AB]).
   - This is the opposite dependence to Stentor. E02 does not try to reconcile the two.
   - Arm R is labelled *Stentor structure* only.
6. **Spaced training is what produces long-term habituation** (Beck & Rankin 1997 [FT]). E02 adds a massed-versus-spaced
   contrast at equal presentation count and pre-registers each arm's direction.
7. **Most of the first draft's predictions passed by construction.** E02 labels every prediction as either
   *discriminating* or *positive control / guaranteed*. Only discriminating ones count toward a verdict.

## 3. What the research got wrong or missed, and how each is handled

| Problem | Handling |
|---|---|
| The pipeline's verifier **removed a supported claim** (Q4: "protein-synthesis block accelerates habituation and prolongs retention" marked partially supported, though the quoted passage says exactly that). | Claims were checked against the full text directly (Rajan et al. 2026 [FT]). The pipeline's kept/removed labels are not used as evidence anywhere in E02. |
| The pipeline's verifier **kept a wrong expansion** (Q3: "SSA = synaptic strength adaptation"; SSA is stimulus-specific adaptation). | Terminology is taken from primary sources (Ayala & Malmierca 2013, whose title is "Stimulus-specific adaptation …" — fetched this session, title and abstract only [AB]; Ulanovsky et al. 2004 [BG]). |
| The RAG index held 3 unrelated papers, so `rag__check_citations` could not validate anything. | Every citation in E02 carries its own read-depth tag, set when the source was actually read. This limit is stated rather than hidden. |
| Aplysia and *Drosophila* papers were available as abstracts only. | They are cited [AB] and used only for the premise that a local mechanism exists. **No parameter comes from them.** |
| Four sources were listed as unread (Chaloner, Chen, Beck & Rankin, the Stentor preprint). | All four are now read or abstracted (§1). Chen & Rieke was found to be off-topic. |
| The pressure test treated **Arm R's untrained-baseline criterion as something the mechanism could pass**. Rajan & Marshall's own parameters imply that the surface pool **drains** under a block; the organism keeps its baseline through a thresholded output. | E02's analytic prediction for R-base is computed from the published rates **before** any run. That prediction is **FAIL in efficacy terms**. The network's spike output may or may not rescue it, depending on how saturating the E cells' response is. That rescue question is the risky part of the prediction (PREREG P5). |
| The prompt's **B-naive-removal** criterion ("removal in a naive network changes responses by less than the TOST bound") **cannot pass**. Removing a non-zero inhibitory weight disinhibits, by construction. | Restated as the *specificity* of the removal effect: exposed-minus-unexposed change within TOST in a naive network. This is recorded as a departure (§4). |
| The prompt's **H-removal** criterion is **guaranteed** if H has no inhibitory pathway to remove. | In E02 every arm carries the same fixed feedforward-inhibitory pathway, and only B's is plastic. Removal is then a real manipulation in every arm, and H's removal effect is not zero by construction. |

## 4. Where E02 departs from the prompt, and why

1. **The feedforward-inhibitory pathway is present, fixed, in every arm.** The reason is §3, last row. As a
   consequence, E02's A, H and 0 are *not* E01's `std`, `hebb_only` and `none`: they share an extra fixed pathway.
   Nothing is compared across the two experiments.
2. **Arm R has depression off**, as H does, so that R is the receptor mechanism alone. B keeps depression on
   (B = A + learned inhibition, as the prompt specifies). So the B–H comparison differs in depression as well as in
   mechanism. The removal test is read at delays after the slow pool has recovered (≥ 300 s, more than 10 τ_slow),
   where A's contribution is analytically nil.
3. **B-naive removal is restated** as a specificity criterion (§3).
4. **The protocol version.**
   - The **installed** `.agents/protocols/PREREG_PROTOCOL.md` (kit `e64136a`) is binding and has 10 sections.
   - The kit repository holds an **uncommitted draft** that adds:
     - estimands with Monte-Carlo SE;
     - a prior-knowledge section;
     - an `EXPERIMENTS.md` registry;
     - an `Attempt:` header;
     - pilots only on off-list seeds under `exploratory/pilot/`;
     - a sensitivity analysis for every [ARBITRARY] parameter;
     - an "unregistered steps" table.
   - E02 follows the installed 10 sections **and** adopts the draft's additions voluntarily, inside those sections.
     That keeps the file valid under both versions.
   - The kit was updated in this repo to `e64136a` on 2026-09-24 (`ad0f27b`) under the operator's instruction to
     follow the toolkit's rules.
