# sim-neural-memory

Simulations that test how a memory of a sound could be held in neural tissue. They are built as falsification
benches: every mechanism has an off switch, every result sits beside its ablation and a plain baseline, and the
experiments that matter were preregistered in git before they ran. **Most of the results are negative.** Every
result is a statement about these models with their chosen parameters, never a measurement of tissue.

**Status: paused (2026-09-24).** Start with **[`docs/FINDINGS.md`](docs/FINDINGS.md)**, a one-page map of every
result, defect and open question.

## What is here

| Part | Code | Result |
|---|---|---|
| A spiking network (Brian2, AdEx + T-type Ca²⁺ cells) with synaptic tagging and capture, asked to store several sound streams and replay them | `src/neurotape/` | [`docs/results/`](docs/results/RESULTS.md): recall at chance; stream identity survives only in the rank order of firing |
| Reproduction of Luboeinski & Tetzlaff 2021 | `src/neurotape/experiments/repro_lt2021.py` | [`docs/repro/`](docs/repro/REPORT.md): the reference passes; neurotape recalls only with the paper's LIF cell |
| A minimal numpy habituation model (Zilany auditory nerve → relay → depressing synapses → LIF E/I) | `src/neurotape/habituation/` | [`docs/habituation/`](docs/habituation/RESULTS.md) |
| **E01-stentor-map** (preregistered) | `experiments/E01-stentor-map/` | closed, FAIL |
| **E02-local-negative-image** (preregistered) | `experiments/E02-local-negative-image/` | closed, FAIL — depletion keeps no specific memory; a published single-cell receptor model drains untrained responses under a synthesis block |

Where every parameter came from: [`ASSUMPTIONS.md`](ASSUMPTIONS.md). Model versions and what each invalidates:
[`CHANGELOG.md`](CHANGELOG.md). Registry of experiments: [`EXPERIMENTS.md`](EXPERIMENTS.md).

## How the experiments were run

The two preregistered experiments follow the KIT Adaptive Preregistration protocol, vendored in `.agents/`.
Each experiment folder holds its plan (`PREREG.md`), pinned environment (`ENV.lock`), frozen `run.py` and
`analyse.py`, `DEVIATIONS.md`, `RESULTS.md`, raw outputs with checksums, and the verbatim log of the assistant
session that ran it (`conversation.jsonl`). Tags `<EID>-prereg`, `-run` and `-closed` mark the order things
happened in; the pull requests carry timestamped receipts. Much of the code, analysis and writing was produced
by an AI coding assistant (Claude) working under that protocol, directed and reviewed by the author.

## Running it

```bash
uv venv --python 3.11 .venv && uv pip install --python .venv/bin/python -e ".[dev]"
uv pip install --python .venv/bin/python "Cython<3" pandas
uv pip install --python .venv/bin/python --no-build-isolation "cochlea @ git+https://github.com/mrkrd/cochlea.git"
.venv/bin/python -m pytest -q            # ~10 min; builds small Brian2 networks
.venv/bin/ruff check .                   # correctness-only lint (see pyproject.toml)
```

`cochlea` (Zilany et al. 2014 auditory-nerve model) is GPL-3 and is installed, not vendored; the commit used is
pinned in each experiment's `ENV.lock`.

**The quickest check needs none of that:** each experiment's `analyse.py` needs only numpy, scipy and pyyaml and
re-derives every verdict from the committed `outputs/`:

```bash
.venv/bin/python experiments/E02-local-negative-image/analyse.py
```

**Two shared tools are not public.** This repo was split out of a private monorepo and still reads two tools
from it (`src/neurotape/monorepo.py`): a provenance stamper that writes `provenance.json` beside results (no
effect on any number), and a surrogate-data library used for the tape model's secondary IAAFT null. Without
them, the tape decoder skips that null and records `p_iaaft: null` with the reason, the monorepo tests skip, and
anything that needs the stamper raises with an explanation. Nothing is substituted silently. "Reproducibility" in
[`docs/REVIEW.md`](docs/REVIEW.md) lists exactly what runs and what does not.

## Licence

MIT ([`LICENSE`](LICENSE)). `cochlea`, a runtime dependency, is GPL-3 and is installed separately, not included.
The `.agents/` folder is the vendored KIT Adaptive Preregistration kit and carries its own licence.

## Review

[`docs/REVIEW.md`](docs/REVIEW.md) is a critical code and methods review done before release: bugs found,
which results they could affect, and what was fixed.
