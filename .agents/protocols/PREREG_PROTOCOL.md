# PREREG_PROTOCOL.md — Adaptive Preregistration for Model Experiments

**Applies to:** every LLM coding session and every human contributor in this repo.
**Status of this file:** binding. If a task conflicts with it, stop and say so before doing the task.
**Installed by:** the KIT Adaptive Preregistration `prereg` module, which also adds the one-line rule to `AGENTS.md`.

Basis (adapted, not copied verbatim): Adaptive Preregistration for model-based research
(Gould et al. 2025, *Methods Ecol Evol*, doi 10.1111/2041-210x.70311; Git guide at
egouldo.github.io/EcoConsPreReg); Preregistration Deviations Table (Willroth & Atherton 2024,
*AMPPS*, doi 10.1177/25152459231213802); ADEMP simulation-study structure (Siepe et al. 2024,
*Psychol Methods*, doi 10.1037/met0000695); ODD/TRACE requirement to report patterns the model
failed to reproduce; full-environment capture per Vallet et al. 2022 (*Sci Data*,
doi 10.1038/s41597-022-01720-9). Registered Modeling Reports (Vanpaemel 2019) supply the
"risky prediction first" principle.

---

## 0. The five rules (read these even if you read nothing else)

1. **No run before PREREG.** A simulation that produces a result the report will cite may not
   be executed until `experiments/<EID>/PREREG.md` exists, is complete (§3), and is tagged
   `<EID>-prereg`.
2. **The environment is part of the preregistration.** `PREREG.md` names the model tag it runs
   against, and the experiment folder contains a lockfile that pins every dependency. No
   floating versions. Adding a dependency after `-prereg` is a deviation (§5).
3. **Failure closes the version; it does not edit it.** If pre-registered criteria fail, tag
   `<EID>-closed`, write `RESULTS.md` with the failure, and open a new experiment ID. Never
   amend `PREREG.md` after `-prereg` to make a failed result pass.
4. **Every departure from the plan goes in `DEVIATIONS.md`,** dated, with whether the outcome
   was known at the time. A deviation that is not logged is a protocol violation, not a
   judgement call.
5. **Exploratory work is quarantined.** Anything not in `PREREG.md` lives under
   `experiments/<EID>/exploratory/` and is labelled exploratory in every report that mentions it.

---

## 1. Repository layout

```
model/                       # the simulator. Versioned with semver tags: model-vX.Y.Z
experiments/
  <EID>/                     # e.g. E04-stentor-map
    PREREG.md                # written BEFORE any scoring run (§3)
    ENV.lock                 # pinned environment (§4)
    config.yaml              # every parameter; model tag; seeds
    run.py                   # the only entry point that produces citable results
    DEVIATIONS.md            # Willroth-Atherton table (§5)
    RESULTS.md               # written AFTER the run, against PREREG.md (§6)
    exploratory/             # post-hoc work; never cited as a preregistered result
    outputs/                 # raw outputs, checksummed
CHANGELOG.md                 # model/ changes and which experiments each invalidates
ASSUMPTIONS.md               # standing modelling assumptions with provenance tags
DEFERRED.md                  # ideas explicitly not pursued yet
```

One experiment = one folder = one prediction set. A new prediction set is a new EID even if
the code is identical.

---

## 2. Version and tag conventions

| Tag | When | Immutable after? |
|---|---|---|
| `model-vX.Y.Z` | Any change to `model/` that alters numerical output | Yes |
| `<EID>-prereg` | Commit that adds a complete `PREREG.md` + `ENV.lock` + `config.yaml` | Yes |
| `<EID>-interim-N` | Adaptive stage N plan revision, before its dependent run (§3.4) | Yes |
| `<EID>-run` | Commit that adds `outputs/` + `RESULTS.md` | Yes |
| `<EID>-closed` | Experiment is finished, pass or fail | Yes |

- Tags are annotated (`git tag -a`) with the ISO date in the message.
- `model/` changes bump the version. An experiment's `config.yaml` records the exact
  `model-v*` it ran against. If the model is patched later, the old result stands as-is and
  `CHANGELOG.md` states which experiments the patch invalidates. Re-running under the new model
  is a new EID.
- Bit-for-bit reproducibility of every previous `<EID>-run` is checked in CI (or manually,
  and stated) before any `model-v*` tag is pushed.
- Optional external timestamp: push `<EID>-prereg` to Zenodo or Software Heritage, use an
  RFC 3161 git hook, or post a tag receipt to the experiment's PR (see companion
  `EXPERIMENT_PR_LOG.md` if adopted). Record the identifier in `PREREG.md §10`. Local git
  dates alone are not tamper-evident; say so if that's all you have.

---

## 3. PREREG.md — required sections

A `PREREG.md` missing any section below is incomplete; do not tag `-prereg`.

```markdown
# <EID> — <one-line title>
Preregistered: <ISO date>   Model tag: model-vX.Y.Z   Author: <name or "LLM session + name">

## 1. Question
One sentence. Mechanistic claim, not "explore".

## 2. Prediction(s) — risky, numeric, directional
P1: ...   (what the hypothesis says will happen)
P2: ...
State for each what result would COUNT AGAINST the hypothesis.

## 3. Pass / fail criteria (numbers written before any output is seen)
| Criterion | Metric | Pass threshold | Fail threshold | Pre-registered value/derivation |
Analytic predictions (e.g. expected slope for a two-stage cascade) are derived HERE, not after.

## 4. Falsifiers
What outcome would weaken the hypothesis enough to close this line of work.

## 5. Model specification
Equations, parameters, units. Each parameter tagged [LIT: doi] / [DERIVED] / [ARBITRARY].
Anything [ARBITRARY] that the result turns out to be sensitive to invalidates the pass.

## 6. Design
Conditions, seeds (fixed list), N per arm, controls (plasticity-off, surrogate/shuffled,
null model). Analysis window. Exclusion rules for failed runs.

## 7. Environment
Language + version, `ENV.lock` checksum, hardware/OS, execution target (e.g. Brian2
`prefs.codegen.target`), thread count. Same seed ≠ same result across targets — pin it.

## 8. Adaptive stages (optional)
If the plan has stages whose later design depends on earlier output, list them. Each
stage revision gets its own `-interim-N` tag BEFORE the run it governs.

## 9. Open decisions
Every choice the spec leaves to the implementer, listed here, decided BEFORE the run, and
tagged. Deciding after seeing output = deviation.

## 10. Timestamp / archive
External identifier (Zenodo DOI, SWHID, RFC 3161 receipt) or "none — local git date only".
```

### 3.4 Adaptive revisions (this is what makes it *adaptive*, per Gould et al.)
Iterative modelling is allowed. The rule is ordering, not rigidity: any plan change is
committed and tagged `<EID>-interim-N` *before* the run it affects, and logged in
`DEVIATIONS.md` with `outcome_known = no`. A plan change after seeing the run's output is
still allowed, but it is logged with `outcome_known = yes` and cannot be used to convert a
fail into a pass.

---

## 4. ENV.lock

- Python: `uv.lock` or `conda-lock.yml` with hashes. R: `renv.lock`. Nix/Guix manifest
  preferred where available (captures the full build graph, not just top-level packages).
- Record `sha256` of the lockfile in `PREREG.md §7`.
- Minimise *unnecessary* dependencies, but full capture beats a short list: a bare interpreter
  already pulls hundreds of transitive binaries.
- Compiled backends (Brian2 cpp_standalone, cython) and BLAS variant are dependencies. Name
  them.

---

## 5. DEVIATIONS.md — required schema

One row per departure from `PREREG.md`. Adapted from Willroth & Atherton 2024.

```markdown
| # | Date | Stage/section | Type | Original text | Change | Reason | Outcome known? | Effect on interpretation | Commit |
|---|------|---------------|------|---------------|--------|--------|----------------|--------------------------|--------|
```

`Type` ∈ {design, model, parameter, analysis, environment, exclusion, criterion}.
`Outcome known?` ∈ {no, partial, yes}. A `yes` on a `criterion` row means the experiment
cannot be reported as a preregistered pass. Empty table = state "No deviations" explicitly.

---

## 6. RESULTS.md — required sections

```markdown
# <EID> — Results
Run tag: <EID>-run   Model tag: ...   ENV.lock sha256: ...   Runs: N, failed: M

## 1. Criteria table
| Criterion | Pre-registered threshold | Observed | Pass/Fail |
Verbatim thresholds from PREREG.md §3. No new criteria here.

## 2. Verdict
PASS / FAIL / UNINTERPRETABLE, one sentence each on why.

## 3. Patterns the model FAILED to reproduce
(ODD/TRACE requirement.) List every qualitative or quantitative target it missed, including
ones outside the pre-registered criteria.

## 4. Sensitivity
Every [ARBITRARY] parameter the result depended on.

## 5. Controls
Each control's result. A stage without its control is not reported as a result.

## 6. Exploratory (clearly labelled)
Anything from exploratory/. Never mixed into §1.

## 7. What only worked because it was tuned
Explicit list. "None" must be stated, not implied.

## 8. Next EID
If FAIL or UNINTERPRETABLE: the new experiment ID and what its prereg will change. This
experiment stays closed.
```

---

## 7. Rules for the LLM session specifically

- **Before any `run.py` execution**, print the `-prereg` tag hash and confirm `PREREG.md`
  has all ten sections. If not, write it and stop for the human to review; do not run.
- **Never** edit `PREREG.md` after `-prereg`. Plan changes go in `DEVIATIONS.md` and, if
  pre-run, an `-interim-N` tag.
- **Never** delete, rewrite, or "clean up" a closed experiment folder.
- **Never** move a post-hoc analysis out of `exploratory/`.
- When asked to "make it pass", "fix the threshold", or "try a few values and keep the best":
  do the runs under `exploratory/`, report them as exploratory, and say plainly that they are
  not preregistered evidence.
- In every report, state read depth for each cited source: [FT] full text, [AB] abstract,
  [BG] background knowledge, [USER] user-supplied.
- State every open decision (PREREG §9) *before* the run that depends on it, in the chat and
  in the file.
- If the human asks you to skip any of this, comply only after writing the skip itself into
  `DEVIATIONS.md` with `outcome_known` filled in honestly.

---

## 8. Minimal commands

```bash
# new experiment
mkdir -p experiments/E05-name/{exploratory,outputs}
# ... write PREREG.md, config.yaml, ENV.lock ...
git add experiments/E05-name && git commit -m "E05: preregistration"
git tag -a E05-prereg -m "$(date -I) preregistered"

# adaptive revision before a dependent run
git commit -am "E05: interim plan 1 (see DEVIATIONS.md #1)"
git tag -a E05-interim-1 -m "$(date -I)"

# after run
git add experiments/E05-name/outputs experiments/E05-name/RESULTS.md
git commit -m "E05: run + results"
git tag -a E05-run -m "$(date -I)"
git tag -a E05-closed -m "$(date -I) verdict: FAIL"

# model change
git tag -a model-v0.4.0 -m "$(date -I) invalidates: E03 (see CHANGELOG.md)"
```

---

## 9. What this protocol does not give you

- Credibility to outsiders without an external timestamp (§2) or a reviewer of the prereg.
- Protection against a wrong model of the biology. It protects the *record*, not the idea.
- Any exemption for "quick checks". A quick check that ends up in a report was a run.
