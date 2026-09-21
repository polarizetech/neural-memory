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

## B3. Adaptive tuning offsets — **sign unsettled**

- **Biology.** After adaptation, a cell's or population's tuning shifts. The literature reports **both**
  directions: attractive shifts (tuning moves *toward* the adapter) and repulsive shifts (tuning moves *away*).
  Which occurs depends on area, stimulus dimension, adapter duration and how tuning is measured.
  **`MEMORY` — no source read in any session; the operator flagged the sign as unsettled.** Confidence that a
  shift exists: high. Confidence in its sign for any given circuit: low.
- **What already exists.** `mechanisms.prior_repulsion` (C4 option) implements *one* sign — a recent-use variable
  that raises threshold ("seek novel") — behind its own switch, default off, labelled sign-unsettled.
- **Proposed implementation.** A per-cell *tuning offset* rather than a threshold: shift the cell's effective
  input weights along the input-channel axis after use, with a signed gain `k_shift` so both signs are one
  parameter apart and can be run as paired conditions.
- **Why deferred.** A tuning offset changes *what* a cell represents; with recall at zero there is no
  representation whose drift could be measured.
- **Precondition.** Recall above the foreign-stream null, and the repeated-recall drift measurement (C7) showing
  a baseline drift to compare against.
- **Falsifier.** Run both signs. The mechanism is uninformative if the two signs are indistinguishable on
  stored-trace drift and on allocation overlap between successively stored items; it is *wrong for this model*
  if either sign raises interference above the no-shift model's CI.

## B4. GRN-style multi-node internal state per cell

- **Biology / theory.** Gene-regulatory-network models show **dynamical memory without any change of topology**:
  training by stimulus history alone moves the network between attractors of fixed wiring. Biswas, Manicka,
  Hoel & Levin 2021, *iScience* 24:102131 — operator-supplied, **unread (title and summary only)**. Confidence that
  the phenomenon exists in GRN models: moderate, from the summary. Confidence it transfers to a neuron's
  excitability state: low. **Capacity is likely small** — a handful of attractors per node set, not a content store.
- **Proposed implementation.** Replace the single CREB-like scalar with a small per-cell dynamical system (3–5
  coupled nodes with saturating interactions, fixed wiring, driven by somatic calcium), read out as the same
  two effects C1 already has (threshold, adaptation). It would let a cell hold more than one excitability
  *regime* and switch between them by input history.
- **Why deferred.** C1 established the single-scalar version and nothing has yet shown a scalar to be the
  limit. A multi-node state multiplies free parameters for a system currently producing nulls.
- **Precondition.** C1 shown to matter (its ablation's CI clear of zero on allocation or reactivation), **and** a
  specific failure a scalar cannot express.
- **Falsifier.** Matched on parameter count against the scalar version: the multi-node state must hold ≥ 2
  history-dependent regimes that survive a delay with synaptic plasticity **off**, and improve a pre-stated
  metric over the scalar with its CI above zero. Otherwise it is complexity without capacity.

## B5. Slow extracellular field

- **What it is.** A coarse scalar field over the network, driven by recent local spiking, with slow decay and
  diffusion, feeding back into per-cell threshold and plasticity rate.
- **Biology (operator-supplied; read depth: abstracts / titles, none read by this build).**
  Astrocytic K⁺ buffering modulates neuronal excitability (PubMed 28279812). Astrocyte Kir4.1 level gates LTP and
  spreading depolarisation (*Cell Reports* 2025, S2211124725000701). Extracellular Ca²⁺ modulates excitability
  within milliseconds, including via ephaptic coupling (*Cells* 2025, 14:1709). Confidence: moderate that such
  slow ionic variables modulate excitability; low on magnitudes and time constants for any specific circuit.
- **Counterpoint, recorded.** K⁺ handling may be **homeostatic only** — clamping the extracellular space rather
  than signalling — with glial signalling carried by Ca²⁺ waves instead. If so, the right variable is a glial
  Ca²⁺ wave, not a K⁺ field, and its dynamics (regenerative, propagating) are different in kind.
- **Design reference.** BETSE (Pietak & Levin 2016; github.com/betsee/betse; in this monorepo at
  `simulators/betse`) — for the **architecture** of coupling a slow ionic/biochemical layer to electrical
  dynamics: separate state, separate (slow) clock, explicit flux terms between layers. **Borrow the architecture,
  not the code.**
- **Proposed implementation.** Place E cells on a ring or grid; one field variable per coarse patch;
  `dF/dt = −F/τ_F + D∇²F + k·(local spike rate)` on a slow clock; feedback `VT += k_V·F`, plasticity rate
  `×(1 + k_P·F)`. Distinct from the existing ephaptic term, which is fast and current-based.
- **Why deferred.** It needs a spatial layout the network does not have, and it is a third slow modulatory
  variable on top of NM and the intrinsic trace while recall is null.
- **Precondition.** Recall above the foreign-stream null; a spatial layout introduced for its own reasons.
- **Falsifier.** Against a **spatially shuffled** field (same statistics, no locality) and against a global
  scalar of the same mean: the local field must change allocation or recall with its CI clear of zero relative to
  both. If the shuffled field does as well, locality — the mechanism's whole content — is doing nothing.

---

## Out of scope in the binaural front end (recorded so they are not rediscovered)

- **Envelope ITD at carriers above ~1.5 kHz.** The MSO stage takes CF ≤ 1.5 kHz only (Verschooten et al.
  2019, *Hear Res* 377:109, PMC6524635 — `HELD`, title only). High-frequency envelope ITD (LSO / envelope-MSO)
  is not modelled.
- **ILD processing (LSO).** The spatialiser *renders* an ILD; nothing downstream computes one. There is no
  LSO anywhere in this monorepo.
- **HRTFs.** The spatialiser is ITD + a smooth ILD shelf; no pinna, elevation or distance cues.
- **The contralateral MSO.** One MSO is modelled (ipsilateral = left).
