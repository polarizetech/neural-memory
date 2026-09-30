# SCOPE_PROTOCOL.md — Claim first: scoping every unit before it is built

**Applies to:** everyone, person or coding assistant, working on a unit: an app, a sim, a tool, a calculator, a
dataset analysis.
**Status of this file:** binding. If a task conflicts with it, stop and say so before doing the task.
**Installed by:** the KIT Adaptive Preregistration `prereg` module, alongside `PREREG_PROTOCOL.md`.
**License:** CC BY 4.0, from [KIT Adaptive Preregistration](https://github.com/polarizetech/adaptive-preregistration). Reuse it with credit.

---

## 0. The rules (read these even if you read nothing else)

1. **The claim first.** Every unit starts with a falsifiable claim, settled with the user in their own words,
   with what would count against it. Nothing is built in a unit until its claim is settled.
2. **Propose; never substitute.** The assistant offers options and records what the user chooses. It never
   replaces the user's claim, design or decision with its own, silently or otherwise.
3. **No scientific feature without a basis and a decision.** Each is assessed against the research, given an
   evidence basis (§5), and built only after the user's decision is recorded (§6).
4. **Unverified sources don't count.** A source the assistant couldn't verify is not a source; if nothing
   verifiable remains, the feature is a gap.
5. **Departures become predictions.** Every override is a place where the unit predicts something. It is
   preregistered in the unit's own `preregistrations/` (§7).

---

## 1. Where this applies, and where the record lives

It applies **automatically to every unit** (`PREREG_PROTOCOL.md` §1): every folder with a `preregistrations/`
folder in a repository that holds several units, or the repository itself when it is one unit. Each unit has
one **scope record**, `SCOPE.toml`, at the unit's root. A unit without one, or with an unsettled claim, is
**unscoped**, and the first work on it is step 1.

What a unit shows before a preregistered test is exploration, not a finding. Exploratory work (apps, tools,
first runs) is the groundwork that makes a later test informative: it settles what the claim's terms mean,
how they are measured, and what the test assumes. Findings come from preregistered experiments.

## 2. Stages

| Stage | The project's stage, if it declares one | What the record must show |
|---|---|---|
| **exploratory** | SKETCH, PROBE | a settled claim; every scientific feature has a basis and a decision; overrides and resolved gaps are allowed, recorded, and labelled as exploratory in the unit itself |
| **production** | BENCH, SHIPPED | every scientific feature is established, supported or derived and uses the research, or is an override whose preregistered experiment has been run, with its result and the decision taken on it recorded |

A unit starts exploratory. Moving it to production is an explicit step the user takes (§3, step 6).

**Pushback at the exploratory stage is one or two sentences.** An absence of evidence is not a reason to
refuse to build: it is recorded as a gap, which blocks that one feature until the user answers one question.
Infrastructure never blocks.

## 3. The process, and the questions asked

The assistant asks **one question at a time**, in this order, and waits for the answer. If it thinks the
user's choice is wrong, it says so once, with its evidence, then records and follows the choice.

**Step 0: setup.** It starts on its own when work begins on an unscoped unit. Without asking unless something
can't be found: which unit this is; where the organisation's conventions and layout are documented (a
conventions document the repository or its profile points to, and existing projects); which research corpus
project it belongs to. It copies `.agents/templates/SCOPE.toml` to the unit's root.

**Step 1: the claim.** The claim is the most important thing a person decides about a unit, so this step is
never skipped or shortened. The assistant proposes three to five candidate claims, each one sentence with a
one-line falsifier.

- *"Which claim should this <app/sim/tool/…> test? Pick one, merge some, or write your own."*

A claim is falsifiable when it says what would be observed if it were wrong. That depends on more than the
sentence: a test of a claim runs through a chain of concepts, measures, assumptions and a prediction, and a
loose link anywhere in that chain means a failed prediction can't count against the claim [1]. So, once the
user has chosen, the assistant asks only for what the answer doesn't already give, one question at a time:

- **Concepts:** *"What exactly do you mean by <term>, here?"* (Only for a term that could be read two ways.)
- **Measure:** *"What will we observe or compute that shows it?"*
- **What counts against it:** *"What result would you take as the claim being wrong?"* A result that would
  support the claim and one that would falsify it are both stated in advance [1].
- **How big:** *"What is the smallest effect that would still matter?"* Stating it is what makes "no effect"
  informative [2]. When too large a result would also be implausible for the mechanism, the claim is a range,
  and a result outside it on either side counts against it [2].
- **Assumptions and boundaries:** *"What does this assume, and where doesn't it apply?"* A negative result
  may come from a wrong assumption rather than a wrong claim [1], so the assumptions are written down with the
  claim.

The claim need not be ready to test. If the user can't yet say how it would be measured or how big an effect
matters, that is recorded as open, and building the unit is how those answers are found [1]. What must be
settled before building is the claim itself and what would count against it.

- *"Recorded as: '…', counting against it: '…'. Is that settled?"*

The user's wording goes into `claim.text` and `claim.counts_against` exactly as given; the other answers go in
their own fields. The assistant never rewords them afterwards; a change is the user's, recorded as a revision.

**Step 2: features.** The assistant proposes features that would test, observe or demonstrate the claim: as a
calculation, a simulation or something a user sees. Each says what it computes or shows (`does`), what outcome
would count against the claim (`counts_against`), and whether it is science or infrastructure (§4).

- *"Which of these do you keep, change or drop?"* (Asked once for the whole list.)

**Step 3: science or infrastructure.** The assistant asks only about parts that could be either, one at a
time:

- *"Is <part> science or infrastructure? Science because …; infrastructure because …"*

**Step 4: evidence, one scientific feature at a time.** The assistant searches the research corpus (citing its
claims by ID) and the literature, assigns a basis (§5), and presents what it found: the proposed basis, each
source with how deeply it was read, and plainly what it couldn't find or verify (`not_found`).

- *"<feature>: use the research, override it, or research further?"*
- If override: *"What are you departing from, and why?"* The answer is recorded verbatim.

**Step 5: predictions.** For each override, the assistant drafts a prediction (§7): what we expect to see
given the inputs and the function, what would count against it, and what the unit has already shown.

- *"Preregister this in <unit>/preregistrations/, adjust it, or leave it for later?"*

**Step 6: production.** Only when the user asks. The assistant runs `scope-status`, lists everything that
stands in the way, and asks:

- *"Move <unit> to production?"*

## 4. Science and infrastructure

- **Infrastructure** is the assistant's to decide without asking: the stack, interface components and
  interaction, typing, linting, layout, tests, CI. It follows the organisation's conventions and stays minimal
  and readable. This protocol holds no conventions of its own; it only says where they come from (step 0).
- **Science** is anything that implements a research concept: equations, models, parameters, transforms,
  thresholds, interpretations.
- **Presentation can be science.** If a choice changes what someone looking at the unit would conclude (a
  colour scale that implies a threshold, a label that implies certainty, which of two values is shown), it is
  a scientific feature.
- When it's unclear which side something falls on, the assistant asks (step 3).

## 5. The evidence basis

Every scientific feature gets one basis. The scale extends the parameter tags of `PREREG_PROTOCOL.md` §3
(section 5) from parameters to features, so a feature that moves into an experiment carries its tag with it.

| Basis | Means | Needs | Tag in `PREREG.md` |
|---|---|---|---|
| `established` | Settled science: in standard references or textbooks, or replicated independently. Not theory, and not best practice alone. One paper is never enough. | at least one verified source | `[LIT: …]` |
| `supported` | Peer-reviewed theory, or accepted and documented best practice. | at least one verified source | `[LIT: …]` |
| `derived` | Built from established or supported parts by a stated derivation, with no source for the whole. Its first run is itself a prediction. | the sources for its parts, and the derivation | `[DERIVED: from …]` |
| `override` | The user's deliberate departure from established or supported practice, for exploratory reasons. | what it departs from; the user's reasoning, verbatim; the date | `[ARBITRARY]`, departure stated |
| `gap` | No research found. An open state: it can't be built until the user overrides it (which makes it an override, departing from "no research found") or asks for more research. | nothing yet | none |

- **When unsure between two bases, take the lower one.**
- **A feature can't be stronger than its source.** Where a source is a claim in the research corpus and the
  corpus grades its claims, the feature's basis can't claim more than that grade supports.
- **Sources are verified, not remembered.** Each is a corpus claim ID (`claim:<ID>`), or a DOI or URL with the
  depth it was read at (`[FT]` full text, `[AB]` abstract), as in `PREREG_PROTOCOL.md` §7. A source that can't
  be resolved is left out and named in `not_found`.

## 6. Decisions

For each scientific feature the user chooses, one feature at a time:

- **use the research**: build it as the research describes (established, supported or derived only);
- **override**: build it the user's way; the reasoning is recorded verbatim, the basis becomes `override`;
- **research further**: the feature stays blocked until the user chooses again.

**Decisions are never edited in place.** A change is appended to `[[revisions]]` with its date, what it
changed from and to, the reasoning, and whether the outcome was already known (as `DEVIATIONS.md` does in
`PREREG_PROTOCOL.md` §5), and the feature is updated.

## 7. Overrides become predictions

An override says "we expect this to work here even though the research doesn't say so". That is a prediction,
and it is tested the way `PREREG_PROTOCOL.md` tests predictions, in the unit's own `preregistrations/`:

- **The prediction** states what we expect to see given the inputs and the function, and what would count
  against it (`PREREG.md` §2–4).
- **What the unit already showed is prior knowledge.** Once the unit has been used on some data, a prediction
  about that same data is not risky [3]. The experiment's `PREREG.md` §8 names what the unit showed, and the
  test uses data the unit hasn't seen.
- **An override that sets a value is an `[ARBITRARY]` parameter,** so the experiment's preregistered
  sensitivity analysis (`PREREG.md` §6) covers it.
- **The feature's `experiments` field links to it** (its EID). Findings that bear on the research corpus are
  written there, referenced by claim ID.
- **When the result is in,** `result` records where it is and the decision taken on it. A failed prediction
  doesn't silently stand: before production the user revises the feature, drops it, or keeps it with a stated
  reason, recorded as a revision.

A derived feature's first run is a prediction too. It needs an experiment only if the unit moves to
production relying on it without independent support.

## 8. Moving to production

At the user's request, the assistant runs `.agents/tools/scope-status`, lists everything under "Before
production", and resolves nothing on the user's behalf. When the list is empty and the user agrees, `stage`
becomes `production`.

---

## 9. The scope record: format contract (format 2)

Other tools may validate a record without dependencies. This section is the contract they implement.

**File:** `SCOPE.toml`, one per unit, at the unit's root. Every unit is expected to have one; a unit without it
is reported as **unscoped** (an open item, like an unsettled claim), so a validator lists those too. Units are
found as `PREREG_PROTOCOL.md` §1 defines them.

**Syntax: a TOML subset.**
- tables (`[claim]`) and arrays of tables (`[[features]]`, `[[revisions]]`);
- `key = value`, one per line, where a value is a single-line string (basic strings use JSON's escapes, so a
  line break is `\n`), an integer, `true`/`false`, or a flat array of those, which may span lines;
- `#` comments.

Not allowed: multi-line strings, inline tables, dotted keys, and TOML dates (a date is a `"YYYY-MM-DD"`
string). A parser that finds any of these reports an error, even where a full TOML parser would accept it.

**Fields.**

| Where | Field | Required | Values |
|---|---|---|---|
| top | `format` | yes | `2` (format `1`, which named the unit `tool`, is still read) |
| top | `unit` | yes | the unit's name (format 1: `tool`) |
| top | `stage` | yes | `exploratory` or `production` |
| top | `corpus_project` | no | the research corpus project |
| `[claim]` | `text`, `counts_against` | yes, once step 1 is done | the user's wording, verbatim |
| `[claim]` | `decided` | yes, once step 1 is done | `YYYY-MM-DD` |
| `[claim]` | `concepts`, `measure`, `smallest_effect`, `assumptions` | no; empty means still open | the user's answers from step 1 |
| `[claim]` | `candidates` | no | the candidates offered |
| `[[features]]` | `id`, `name` | yes | `id` unique in the record |
| `[[features]]` | `kind` | yes | `science` or `infrastructure` |
| `[[features]]` | `status` | yes | `accepted`, `changed` or `dropped` |
| `[[features]]` | `does`, `counts_against` | science, not dropped | text |
| `[[features]]` | `basis` | science, not dropped, once step 4 is done | `established`, `supported`, `derived`, `override`, `gap` |
| `[[features]]` | `sources` | by basis (below) | `claim:<ID>`, or `doi:10.…` / `https://…` followed by ` [FT]` or ` [AB]` |
| `[[features]]` | `derivation` | `derived` | text |
| `[[features]]` | `departs_from`, `reasoning` | `override` | text; `reasoning` verbatim |
| `[[features]]` | `not_found` | no | text |
| `[[features]]` | `decision` | once the user has decided | `use-research`, `override`, `research-further` |
| `[[features]]` | `decided` | with a decision | `YYYY-MM-DD` |
| `[[features]]` | `experiments` | `override`, before production | the EIDs of preregistered experiments |
| `[[features]]` | `result` | `override`, before production | where the result is, and the decision taken on it |
| `[[revisions]]` | `feature`, `date`, `from`, `to`, `outcome_known`, `reasoning` | all | `feature` is a feature id or `claim`; `outcome_known`: `no`, `partial`, `yes` |

Unknown fields are ignored, so later versions can add fields without breaking an older reader.

**Rules.** A record **breaks the contract** if any of these fail:

1. `format` is 1 or 2; the unit's name (`unit`, or `tool` in format 1) and `stage` are present and valid.
2. Feature ids are unique; `kind` and `status` use the values above.
3. A science feature that isn't dropped has `does` and `counts_against`.
4. `established` and `supported` cite at least one source; `derived` cites its sources and has a
   `derivation`; every source matches the source format.
5. `override` has `departs_from`, `reasoning` and `decided`, and its decision is `override`.
6. `use-research` goes only with `established`, `supported` or `derived`; a `gap` has no decision or
   `research-further`.
7. Every decision has `decided`; every date is `YYYY-MM-DD`.
8. Every revision names a feature in the record, or `claim`, and has all its fields.

A record is **open** while the claim isn't settled, a science feature has no basis or no decision, or an
override has no experiment yet; a feature is **blocked** while its decision is `research-further`. Both are
normal at the exploratory stage.

**At the production stage** a record must also have nothing open or blocked, and every override must have
`experiments` and a `result`.

## 10. `scope-status`

`.agents/tools/scope-status [PATH]` finds the units under PATH (default: the repository) and every `SCOPE.toml`
there. It prints each record's claim, its features with their basis and decision, and its errors, open
items, blocked features and what stands before production, and lists units that have no record yet. It
always exits 0. With `--check` it exits 1 if a record breaks the contract, or a production record isn't
ready, so it can gate CI.

## 11. What this protocol does not give you

- **Correct research.** The record shows that a basis was assigned and a source cited, not that the source says
  what it was cited for. The assistant's summary of a source can be wrong; read depth says how far to trust it.
- **Enforcement.** The rules bind the assistant through its instructions, and `scope-status --check` catches a
  malformed or unfinished record. Nothing stops code being written that the record doesn't describe.
- **Findings.** A unit explores. What it shows becomes evidence only through a preregistered experiment.

---

## References

Read depth: [FT] read in full text, with the passages this protocol relies on checked verbatim; [AB] abstract
plus secondary summaries. The evidence-basis scale in §5 is this protocol's own; it reuses the parameter tags
of `PREREG_PROTOCOL.md`, whose references give their sources.

1. Scheel, A. M., Tiokhin, L., Isager, P. M., & Lakens, D. (2021). Why hypothesis testers should spend less
   time testing hypotheses. *Perspectives on Psychological Science*, 16(4), 744–755.
   https://doi.org/10.1177/1745691620966795 [FT]. The derivation chain from a claim to a test (concepts,
   measures, relationships, boundary conditions and auxiliary assumptions, predictions); stating in advance
   what would support and what would falsify; groundwork before a confirmatory test (§1, §3 step 1).
2. Lakens, D. (2022). Sample size justification. *Collabra: Psychology*, 8(1), 33267.
   https://doi.org/10.1525/collabra.33267 [FT]. The smallest effect size of interest; range predictions (§3
   step 1).
3. Weston, S. J., Ritchie, S. J., Rohrer, J. M., & Przybylski, A. K. (2019). Recommendations for increasing the
   transparency of analysis of preexisting data sets. *Advances in Methods and Practices in Psychological
   Science*, 2(3), 214–227. https://doi.org/10.1177/2515245919848684 [AB]. Declaring what was already seen
   (§7, prior knowledge).
4. Nosek, B. A., Ebersole, C. R., DeHaven, A. C., & Mellor, D. T. (2018). The preregistration revolution.
   *Proceedings of the National Academy of Sciences*, 115(11), 2600–2606.
   https://doi.org/10.1073/pnas.1708274114 [AB]. Keeping prediction distinct from postdiction (§7).
5. Vanpaemel, W. (2019). The really risky registered modeling report: Incentivizing strong tests and HONEST
   modeling in cognitive science. *Computational Brain & Behavior*, 2, 218–222.
   https://doi.org/10.1007/s42113-019-00056-9 [AB]. Risky predictions from models (§7).
6. Gould, E., et al. (2026). 'But I can't preregister my research': Improving the reproducibility and
   transparency of ecology and conservation with adaptive preregistration for model-based research.
   *Methods in Ecology and Evolution*, 17(6), 1768–1787. https://doi.org/10.1111/2041-210x.70311 [AB].
   Staged, adaptive plans for model-based work (§2, §7).
