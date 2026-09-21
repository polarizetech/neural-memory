# DEFERRED — mechanisms documented, deliberately not built

Each entry: the mechanism, the biology with sources and how far each source was read, a proposed
implementation, why it is deferred, the precondition for building it, and the test that would falsify
it. **Nothing on this page exists in the code.** An entry moves into the build only when its precondition
is met, and then as a switchable mechanism with its own ablation.

Read depth: `HELD` = in `tools/paper-library`, not read; `ABSTRACT` = abstract only; `MEMORY` = not retrieved.

---

## Recall-phase drives held behind candidate 1

Candidate 1 (NM raises excitatory excitability) is built — `ASSUMPTIONS.md`. Two more are held, in this order.

### D2. Disinhibitory drive — **ACh-like, not LC**

- **Biology.** Acetylcholine and noradrenaline act separably on hippocampal ensemble formation; in CA3 the
  cholinergic action includes a reduction of feedback inhibition, distinct from noradrenaline's action.
  Prince, Bacon, Humphries et al. 2021, *PLoS Comput Biol* 17:e1009435, doi:10.1371/journal.pcbi.1009435
  (PMC8513881) — `HELD`, title and metadata only. **Confidence: moderate, unread.**
- **Proposed implementation.** A *second* modulator trace `ACh(t)`, separate from `NM(t)`, that scales
  I→E conductance down during the recall probe. It must not be folded into `NM`: the label matters, because
  the basis for candidate 1 is specifically that LC noradrenaline does **not** change inhibitory input.
- **Why deferred.** One recall-phase drive at a time, so a positive can be attributed.
- **Precondition.** Candidate 1's result is in (either way).
- **Falsifier.** With the drive on, recall must match its own stream better than 20 foreign streams
  (whole 95 % CI of own − foreign above zero). Higher firing alone does not count.

### D3. Theta-to-threshold — **last**

- **Mechanism.** Raise the theta pacemaker's amplitude until assembly cells reach threshold on each cycle.
- **Why last.** It can make cells fire **regardless of content**: a strong enough rhythmic current produces
  recall-phase activity in any network, stored trace or not. Any positive from it needs the foreign-stream
  null *and* a frozen-weights control showing the activity is trace-specific.
- **Precondition.** D1 and D2 both null, and 800 E / 200 I tried first (operator's sequencing).

---

## B1. Activity-dependent excitatory/inhibitory transmitter switching

- **Biology.** Chronic activity changes transmitter identity *within the same neuron*: sustained enhanced
  spiking shifts neurons toward an inhibitory transmitter, sustained suppressed spiking toward an excitatory
  one, with other identity markers unchanged. Reported in adult hippocampus, mPFC and dorsal raphe.
  Spitzer 2017, *Annu Rev Neurosci* 40:1–19, doi:10.1146/annurev-neuro-072116-031204 — `HELD`, `ABSTRACT`
  (operator's summary); Meng, Li, Deisseroth et al. 2018, *PNAS* 115(20):5064,
  doi:10.1073/pnas.1801598115 (PMC5960321) — `HELD`, `ABSTRACT`. **Confidence: high for the phenomenon,
  from abstracts only; nothing about rate constants or the fraction of cells that switch has been read.**
- **Proposed implementation.** A slow homeostatic rule on a per-neuron activity average `ā_i` (hours-scale
  time constant, so it takes the 60× compression like the other slow terms). When `ā_i` stays past a
  set-point, the **sign of that neuron's outgoing synapses** flips, gradually (a per-neuron mixing variable
  `s_i ∈ [−1, +1]` multiplying its output, not an instant switch). The cell's **class never changes**: its
  intrinsic parameters, its inputs and its plasticity rule stay those of an excitatory cell.
- **Why deferred.** The current failure is a **silent network at recall**. This rule converts the *most
  active* cells — the ones that encoded the stream — into inhibitory ones, which would deepen the silence
  and remove exactly the cells a readout depends on. Building it now would produce a worse null and teach nothing.
- **Precondition.** Recall r reliably above chance (own − foreign CI above zero, ≥ 10 seeds) in the base model.
- **Falsifier / test.** As a switchable ablation: with switching on, (a) late-phase consolidation and recall
  must not fall below the switching-off model by more than the seed-to-seed CI; (b) the predicted *benefit* —
  activity homeostasis preventing runaway assemblies across many stored items — must show as a lower
  recall-phase firing-rate variance across items. If (a) fails and (b) is absent, the mechanism is a cost.

## B2. Developmental / critical-period phase

- **Biology.** An early window of high plasticity that closes as inhibition matures; adult dentate-gyrus
  neurogenesis keeps a subpopulation of young, hyper-plastic cells. **`MEMORY` — background knowledge, not
  verified in any session. Verify (and cite) before building: Hensch 2005 *Nat Rev Neurosci* for
  inhibition-gated critical periods and the adult-neurogenesis literature are where to start.**
- **Proposed implementation.** A pre-training phase on **varied input with no readout**, plasticity elevated
  (larger `γ_p`, `γ_d` or a lower `θ_tag`), followed by a gradual rise of I→E and gap-junction strength to
  adult values ("inhibitory maturation"); a small fixed fraction of E cells keeps the elevated plasticity
  permanently.
- **Hypothesis.** The early phase builds a representational scaffold that makes later traces **more
  separable** — less smear between stored items.
- **Why deferred.** The predicted benefit is for **interference across many stored items**. The current
  failure is *single-trace* recall; a scaffold cannot help a trace that does not replay at all.
- **Precondition.** Single-trace recall works.
- **Falsifier / test.** Store N items with vs without the developmental phase, everything else equal and
  seeds paired; compare **pairwise recall discriminability** (own-vs-other best-lag r, the foreign-stream
  statistic applied between stored items). The hypothesis fails if the whole 95 % CI of
  (with − without) is not above zero, or if it is above zero only because the developmental phase lowered
  overall activity.

---

## Out of scope in the binaural front end (recorded so they are not rediscovered)

- **Envelope ITD at carriers above ~1.5 kHz.** The MSO stage takes CF ≤ 1.5 kHz only (Verschooten et al.
  2019, *Hear Res* 377:109, PMC6524635 — `HELD`, title only). High-frequency envelope ITD (LSO / envelope-MSO)
  is not modelled.
- **ILD processing (LSO).** The spatialiser *renders* an ILD; nothing downstream computes one. There is no
  LSO anywhere in this monorepo.
- **HRTFs.** The spatialiser is ITD + a smooth ILD shelf; no pinna, elevation or distance cues.
- **The contralateral MSO.** One MSO is modelled (ipsilateral = left).
