"""Analyze audio.mp3 and write a DRAFT musical event map for human review.

Outputs (scripts/out/):
  events.draft.json  - timestamped events (reveal / nextMosaic / finale)
  timeline.png       - waveform with onset ticks, strength and phrase breaks

This is a starting point. Edit the draft by hand into events.json.
"""
import json
from pathlib import Path
import numpy as np
import librosa
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

FINALE_T = 16.25      # provisional; snapped to the nearest big loudness jump
CLUSTER = 0.06        # onsets closer than this are one musical hit
PHRASE_GAP = 0.30     # silence/gap between hits that ends a phrase (seconds)

y, sr = librosa.load(str(ROOT / "audio.mp3"), sr=22050, mono=True)
dur = len(y) / sr
hop = 256
rms = librosa.feature.rms(y=y, hop_length=hop)[0]
t_rms = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)

env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
on_frames = librosa.onset.onset_detect(onset_envelope=env, sr=sr, hop_length=hop, backtrack=False)
on_t = librosa.frames_to_time(on_frames, sr=sr, hop_length=hop)
on_s = env[on_frames] / env.max()

# merge near-simultaneous onsets into hits (keep strongest)
hits = []
for t, s in zip(on_t, on_s):
    if hits and t - hits[-1]["time"] < CLUSTER:
        if s > hits[-1]["strength"]:
            hits[-1].update(time=float(t), strength=float(s))
    else:
        hits.append({"time": float(t), "strength": float(s)})

# snap the finale to the largest loudness jump within +/-0.6 s of the provisional time
w = int(0.08 * sr / hop)
best, best_r = FINALE_T, 0.0
for i in range(w, len(rms) - w):
    if abs(t_rms[i] - FINALE_T) <= 0.6:
        r = rms[i:i + w].mean() / (rms[i - w:i].mean() + 1e-6)
        if r > best_r:
            best, best_r = float(t_rms[i]), float(r)
finale_t = round(best, 2)

# strength -> how many ducks to reveal
def count_for(s):
    return 1 if s < 0.25 else 2 if s < 0.45 else 3 if s < 0.65 else 4 if s < 0.85 else 5

events, phrase_ends = [], []
mosaic_hits = [h for h in hits if h["time"] < finale_t - 0.05]
for i, h in enumerate(mosaic_hits):
    events.append({"time": round(h["time"], 2), "action": "reveal",
                   "count": count_for(h["strength"]), "strength": round(h["strength"], 2)})
    nxt = mosaic_hits[i + 1]["time"] if i + 1 < len(mosaic_hits) else finale_t
    if nxt - h["time"] > PHRASE_GAP:
        phrase_ends.append(round(h["time"], 2))
        events.append({"time": round(h["time"] + 0.12, 2), "action": "nextMosaic",
                       "note": f"gap of {nxt - h['time']:.2f}s follows"})
events.append({"time": finale_t, "action": "finale", "note": f"loudness jump x{best_r:.1f}"})
events.sort(key=lambda e: e["time"])

(OUT / "events.draft.json").write_text(json.dumps(
    {"duration": round(dur, 2), "finale_time": finale_t, "events": events}, indent=1))

# ---- timeline picture ----
W, H = 2400, 360
img = Image.new("RGB", (W, H), "#111")
d = ImageDraw.Draw(img)
px = lambda t: int(t / dur * (W - 20)) + 10
n = 2000
seg = np.array_split(np.abs(y), n)
for i, s in enumerate(seg):
    x = int(10 + i * (W - 20) / n)
    a = float(s.max()) * 150
    d.line([(x, 190 - a), (x, 190 + a)], fill="#6a6adc")
for e in events:
    x = px(e["time"])
    if e["action"] == "reveal":
        d.line([(x, 20), (x, 20 + 14 * e["count"])], fill="#ffd400", width=3)
    elif e["action"] == "nextMosaic":
        d.line([(x, 20), (x, H - 30)], fill="#33cc66", width=2)
    else:
        d.line([(x, 0), (x, H)], fill="#ff3b3b", width=4)
        d.text((x + 6, H - 50), f"FINALE {finale_t}s", fill="#ff7777")
for s in range(int(dur) + 1):
    x = px(s)
    d.line([(x, H - 22), (x, H - 12)], fill="#aaa")
    if s % 2 == 0:
        d.text((x - 8, H - 12), f"{s}s", fill="#aaa")
d.text((10, 4), "yellow = reveal (height ~ count)   green = new mosaic   red = finale", fill="#ccc")
img.save(OUT / "timeline.png")

print(f"duration {dur:.2f}s | hits {len(hits)} | mosaic hits {len(mosaic_hits)} | "
      f"phrase breaks {len(phrase_ends)} | finale {finale_t}s")
