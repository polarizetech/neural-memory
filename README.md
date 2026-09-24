# sim-neural-memory

Simulations for testing how memory could be held in neural tissue, as falsification benches. The Python package
is `neurotape`:

- a spiking network with synaptic tagging and capture that tries to store and replay waveforms (`docs/results/`);
- a reproduction of Luboeinski & Tetzlaff 2021 (`docs/repro/`);
- a minimal habituation-as-memory model (`docs/habituation/`).

**Start with [`CLAUDE.md`](CLAUDE.md)** for setup, what has been run and what each result means, and with
[`ASSUMPTIONS.md`](ASSUMPTIONS.md) for where every number came from.

It needs a checkout of the `polarizetech/audio-projects` monorepo beside it, for shared tools
(`src/neurotape/monorepo.py` explains the lookup and fails loudly without it). Private; split out of that
monorepo on 2026-09-24 with its history.
