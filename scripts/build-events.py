"""Turn events.draft.json into the cleaned events.json used by the page.

Edits (all deterministic, seeded so every build is identical):
  - drop spurious nextMosaic events (too early, or <0.5 s after another)
  - give the beat grid some life: ~22% of weak reveals are skipped and their
    count is added to the NEXT reveal (pause, then a bigger burst)
  - ~10% of remaining reveals get +/-1 duck
The page itself also auto-advances when a mosaic fills, carrying any
leftover count into the next mosaic, so long runs need no hand-placed breaks.
Hand-edit events.json afterwards if you want to tune the choreography.
"""
import json, random
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
d = json.loads((HERE / "out" / "events.draft.json").read_text())
rng = random.Random(180)

COUNT_SCALE = 0.55       # multiplies the detected hit strength -> ducks
MAX_COUNT = 4            # largest single burst
LETTER_LEAD = 0.4        # lettering + underline appear this much before the spoken-line estimate
BLACK_LEAD = 0.5         # screen goes fully black this long before the finale split; no reveals in that gap
SPOKEN_ESTIMATE = 21.0   # estimate; refine when the bunny-duck finale is built
IRIS_START = 23.05       # circle closes to black, audio ends at ~23.86

events, last_break, carry, first = [], -9, 0, True
for e in sorted(d["events"], key=lambda x: x["time"]):
    if e["action"] == "nextMosaic":
        if e["time"] < 0.5 or e["time"] - last_break < 0.5:
            continue
        last_break = e["time"]
        events.append({"time": e["time"], "action": "nextMosaic"})
    elif e["action"] == "reveal":
        c = max(1, round(e["count"] * COUNT_SCALE))   # fewer ducks per hit overall
        if first:
            c = 1                                      # gentle opening
        if not first and c <= 1 and rng.random() < 0.22:
            carry += c
            continue
        if rng.random() < 0.10:
            c = max(1, c + rng.choice([-1, 1]))
        c = min(MAX_COUNT, c + carry)
        carry, first = 0, False
        events.append({"time": e["time"], "action": "reveal", "count": c})
    elif e["action"] == "finale":
        events.append({"time": e["time"], "action": "finale"})

# black gap before the split: drop late reveals, clear the mosaic
cut = round(d["finale_time"] - BLACK_LEAD, 2)
events = [e for e in events if not (e["action"] in ("reveal", "nextMosaic") and e["time"] >= cut)]
events.append({"time": cut, "action": "clear"})
events.sort(key=lambda e: e["time"])

out = {
    "duration": d["duration"],
    "finale_time": d["finale_time"],
    "spoken_time": SPOKEN_ESTIMATE,
    "iris_start": IRIS_START,
    # finale choreography (seconds on the audio clock); tune freely
    "cues": {
        "bunny": round(d["finale_time"] + 0.6, 2),      # bunny + duck pop in
        "lettering": round(SPOKEN_ESTIMATE - LETTER_LEAD, 2),  # "That's all Folks!" wipes in
        "line": round(SPOKEN_ESTIMATE - LETTER_LEAD + 0.9, 2),  # red underline follows the lettering
        "wink": round(SPOKEN_ESTIMATE + 1.3, 2),        # bunny winks, duck squashes
        "winkEnd": round(SPOKEN_ESTIMATE + 2.0, 2),
    },
    "events": events,
}
(ROOT / "events.json").write_text(json.dumps(out, indent=1))
r = [e for e in events if e["action"] == "reveal"]
print(f"{len(r)} reveals ({sum(e['count'] for e in r)} ducks), "
      f"{sum(e['action'] == 'nextMosaic' for e in events)} breaks -> events.json")
