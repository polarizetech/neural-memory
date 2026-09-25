"""Write a single-cell run as one self-describing JSON for the viewer (apps/singlecell-viewer).

Every file says what it is: tier MODELLED (a simulation, never a measurement), the model and its source, the
config with every switch, the protocol, dense traces, per-event results and one seeded sampled cell. The viewer
reads nothing else, so a figure can never lose its label on the way to the screen."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import sim
from .models import SOURCE_RM2025, CellConfig

SCHEMA = "neurotape.singlecell.trace/1"


def export(path: str | Path, cfg: CellConfig, protocol: list[sim.Stim], *, title: str, notes: list[str],
           channel_names: list[str] | None = None, t_end: float | None = None, probe_force: float | None = None,
           sample_dt: float = 0.25, seed: int = 0, provenance: dict | None = None) -> dict:
    res = sim.run(cfg, protocol, t_end=t_end, probe_force=probe_force, sample_dt=sample_dt)
    doc = dict(
        schema=SCHEMA, tier="MODELLED", title=title, notes=notes,
        model=dict(name="Stentor receptor inactivation" if cfg.mechanism == "internalisation"
                   else "Stentor receptor gating (Wood variant)", source=SOURCE_RM2025,
                   engine="libRoadRunner (Tellurium) for continuous dynamics; stimulus jumps as in the authors' code"),
        channels=channel_names or [f"channel {c}" for c in range(cfg.n_channels)],
        config=res["config"], protocol=[s.__dict__ for s in protocol],
        trace=res["trace"], events=res["events"], sampled_cell=dict(seed=seed, responses=sim.sample_responses(res, seed)),
        provenance=provenance or {},
    )
    text = json.dumps(doc, indent=1, default=float)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return dict(path=str(p), sha256=hashlib.sha256(text.encode()).hexdigest(), n_events=len(res["events"]))
