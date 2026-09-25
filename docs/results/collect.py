"""Copy each experiment's REPORT/summary/runs/figures out of the gitignored results/ folder, and compute
the ENCODE-side paired differences the ablation report does not print. Re-runnable."""
import json, shutil, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from neurotape.experiments.common import paired_diff, fmt

HERE, RES = Path(__file__).parent, Path(__file__).resolve().parents[2] / "results"
latest = {}
for d in sorted(RES.glob("*_*")):
    if (d / "REPORT.md").exists():
        latest[d.name.split("_", 1)[1]] = d
for name, d in latest.items():
    out = HERE / name; out.mkdir(exist_ok=True)
    for f in list(d.glob("*.md")) + list(d.glob("*.json")) + list(d.glob("*.png")) + list(d.glob("*.yaml")):
        shutil.copy(f, out / f.name)
print("collected:", ", ".join(latest))
ab = latest.get("exp3_ablations")
if ab:
    runs = [r for r in json.load(open(ab / "runs.json")) if r.get("ok")]
    by = {}
    for r in runs:
        by.setdefault(r["tag"], {})[r["seed"]] = r
    full = by["full"]; lines = ["| condition | full - this, ENCODE held-out r | LOADED frac | late-phase synapse frac |", "|---|---|---|---|"]
    for tag, rs in by.items():
        seeds = sorted(set(rs) & set(full))
        d = paired_diff([np.mean(full[s]["encode_heldout_r"]) for s in seeds], [np.mean(rs[s]["encode_heldout_r"]) for s in seeds])
        verdict = "-" if tag == "full" else ("mechanism HELPS encoding" if d["beats"] else ("ablation is BETTER" if d["hi"] < 0 else "no detectable effect"))
        lines.append(f"| {tag} | {fmt(d)} {verdict} | {np.mean([rs[s]['state_frac_encode'][1] for s in seeds]):.3f} | {np.mean([rs[s]['frac_late'] for s in seeds]):.4f} |")
    (HERE / "exp3_ablations" / "ENCODE_SIDE.md").write_text("## Ablations, encode side (computed from runs.json by collect.py)\n\n" + "\n".join(lines) + "\n")
    print("\n".join(lines))
