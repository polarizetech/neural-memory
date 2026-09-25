"""Pilot (PREREG_PROTOCOL 3.5): exercises run.py and analyse.py end to end on a SYNTHETIC protocol set -- forces
0.7 / 1.2 (not the preregistered 1.0 / 1.5), 5-tap training, 1 h instead of 12 h, one sensitivity setting -- and
prints ONLY whether each piece ran. No criterion value is printed or written outside exploratory/pilot/."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
import analyse  # noqa: E402
import run  # noqa: E402

c = copy.deepcopy(run.load_cfg())
c["force"] = {"level3": 0.7, "level4": 1.2}
for p in ("puro_short", "chx_short", "puro_short_15"):
    c["protocols"][p]["n"] = 5
c["protocols"]["long"]["n"] = 60
c["protocols"]["untrained_long"]["tap_at_min"] = [60, 150]
c["arms"]["k_deg_scale"] = [1.0, 0.001]
c["sensitivity"] = [{"name": "smoke_s", "k_x": 0.05}]
c["exports"] = c["exports"][:1]
out = Path(__file__).parent / "out"
out.mkdir(exist_ok=True)
rows = run.one_setting(c, dict(name="main")) + run.one_setting(c, c["sensitivity"][0])
print("protocol runs ok:", sum(r["ok"] for r in rows), "/", len(rows))
bad = [r["error"] for r in rows if not r["ok"]]
if bad:
    print(bad[0])
g = run.gate_rows(c)
print("gate rows ok:", sum(r["ok"] for r in g), "/", len(g))
ct = run.content_rows(c)
print("content rows:", len(ct))
ix = analyse.index([r for r in rows if r["ok"]])
c["protocols"]["untrained_long"]["tap_at_min"] = [60, 150]
# analyse keys the recovery reference on level4@810; the smoke protocol uses 150, so alias it
for r in rows:
    if r["protocol"] == "untrained_long" and r["ok"]:
        r["untrained"]["level4@810"] = r["untrained"]["level4@150"]
for a in {r["arm"] for r in rows}:
    analyse.score_arm(c, ix, "main", a, next(x["gate"] for x in g if x["arm"] == a))
    analyse.score_arm(c, ix, "smoke_s", a)
print("analyse.score_arm ran on", len({r['arm'] for r in rows}), "arms x 2 settings")
(out / "smoke.json").write_text(json.dumps(dict(n_rows=len(rows), n_ok=sum(r["ok"] for r in rows)), indent=1))
