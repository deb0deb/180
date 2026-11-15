"""Render the finale page to an MP4 (H.264 + AAC), frame by frame.

Drives the real page in headless Edge with a virtual clock, so every frame is exact.
Audio is audio.mp3 plus the synthesized wink twink, mixed at the right time.

  python render-video.py [--seed 7] [--fps 30] [--hold 3] [--limit N] [--out file.mp4]

Needs the local server running:  python -m http.server 8000   (from the project folder)
Output goes to scripts/out/ (not committed).
"""
import argparse, base64, json, subprocess, sys, time, wave, shutil, urllib.request
from pathlib import Path
import numpy as np
import imageio_ffmpeg

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "out"
URL = "http://localhost:8000/"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
W, H = 1080, 1920          # output size (portrait 9:16)

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=7, help="which random duck cast to render")
ap.add_argument("--fps", type=int, default=30)
ap.add_argument("--hold", type=float, default=3.0, help="seconds to hold the end card")
ap.add_argument("--limit", type=int, default=0, help="render only N frames (testing)")
ap.add_argument("--out", default="duck-finale.mp4")
args = ap.parse_args()

cfg = json.loads((ROOT / "events.json").read_text())
duration = cfg["duration"]
total = duration + args.hold
nframes = int(round(total * args.fps)) if not args.limit else args.limit
frames = OUT / "frames"
if frames.exists():
    shutil.rmtree(frames)
frames.mkdir(parents=True)

try:
    urllib.request.urlopen(URL, timeout=3)
except Exception:
    sys.exit("Local server not running. In the project folder run: python -m http.server 8000")

# Fake audio clock + seeded randomness, installed before the page loads.
INIT = """
(() => {
  let s = %d >>> 0;
  Math.random = () => { s = (s + 0x6D2B79F5) | 0; let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  let t0 = null, fired = false; window.__t0epoch = null; const DUR = %f;
  const P = HTMLMediaElement.prototype;
  Object.defineProperty(P, 'currentTime', { configurable: true,
    get() { return t0 === null ? 0 : (performance.now() - t0) / 1000; },
    set(v) { t0 = v === 0 ? null : performance.now() - v * 1000; } });
  P.play = function () { if (t0 === null) { t0 = performance.now(); window.__t0epoch = Date.now(); } return Promise.resolve(); };
  P.pause = function () {};
  Object.defineProperty(P, 'ended', { configurable: true,
    get() { return t0 !== null && (performance.now() - t0) / 1000 >= DUR; } });
  const watch = () => { const a = document.getElementById('snd');
    if (a && !fired && t0 !== null && (performance.now() - t0) / 1000 >= DUR) { fired = true; a.dispatchEvent(new Event('ended')); }
    requestAnimationFrame(watch); };
  requestAnimationFrame(watch);
})();
""" % (args.seed, duration)

import asyncio
from playwright.async_api import async_playwright

async def capture():
    """Play the page in real time (fake audio clock = real clock) and record
    screencast frames with timestamps; resample to a constant frame rate after."""
    got = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        ctx = await browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=1)
        page = await ctx.new_page()
        await page.add_init_script(INIT)
        await page.goto(URL, wait_until="load")
        await page.add_style_tag(content="#start{display:none!important}")
        await page.wait_for_function("document.getElementById('start') && !document.getElementById('start').disabled")
        await page.evaluate("""async () => {
          const m = await (await fetch('assets/duck-thumbnails/manifest.json')).json();
          const files = m.map(x => 'assets/duck-thumbnails/' + x.file).concat(
            ['01-concentric-rings','02-body','03-head','04-wink','05-duck-on-hand','06-lettering','07-underline','you-did-it'].map(n => 'assets/finale/' + n + '.png'));
          window.__keep = await Promise.all(files.map(f => new Promise(r => { const i = new Image(); i.onload = i.onerror = () => r(i); i.src = f; })));
          await Promise.all(window.__keep.map(i => i.decode ? i.decode().catch(() => {}) : 0));
        }""")
        await page.wait_for_timeout(800)
        cdp = await ctx.new_cdp_session(page)

        def on_frame(ev):
            got.append((ev["metadata"]["timestamp"], base64.b64decode(ev["data"])))
            asyncio.ensure_future(cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]}))
        cdp.on("Page.screencastFrame", on_frame)
        await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "maxWidth": W, "maxHeight": H, "everyNthFrame": 1})
        await page.wait_for_timeout(300)
        await page.evaluate("document.getElementById('start').click()")   # the tap
        t0 = await page.evaluate("window.__t0epoch")
        await page.wait_for_timeout(int((total + 0.5) * 1000))
        await cdp.send("Page.stopScreencast")
        await browser.close()
    return t0, got

t_start = time.time()
t0, got = asyncio.run(capture())
print(f"captured {len(got)} raw frames in {time.time() - t_start:.0f}s", flush=True)
got.sort(key=lambda x: x[0])
ts = np.array([g[0] for g in got])
t0s = t0 / 1000.0
for i in range(nframes):
    k = int(np.searchsorted(ts, t0s + i / args.fps, side="right")) - 1
    (frames / f"{i:05d}.jpg").write_bytes(got[max(k, 0)][1])

# ---- audio: track + twink at the wink cue ----
wav_in = OUT / "music.wav"
subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(ROOT / "audio.mp3"), "-ar", "44100", "-ac", "2", str(wav_in)], check=True)
with wave.open(str(wav_in)) as w:
    sr = w.getframerate(); ch = w.getnchannels()
    pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
pcm = pcm.reshape(-1, ch)
n_total = int(sr * total)
mix = np.zeros((n_total, ch), np.float32); mix[:len(pcm)] = pcm[:n_total]

def twink(t0):
    for f, d in [(1976, 0.0), (2637, 0.09), (3136, 0.18)]:
        n = int(sr * 0.5); t = np.arange(n) / sr
        env = np.where(t < 0.01, 0.0001 * (0.5 / 0.0001) ** (t / 0.01), 0.5 * (0.0001 / 0.5) ** ((t - 0.01) / 0.49))
        s = (np.sin(2 * np.pi * f * t) * env).astype(np.float32)
        a = int(sr * (t0 + d)); b = min(a + n, n_total)
        if b > a:
            mix[a:b] += s[: b - a, None]
twink(cfg["cues"]["wink"])
mix = np.clip(mix, -1, 1)
wav_out = OUT / "mix.wav"
with wave.open(str(wav_out), "wb") as w:
    w.setnchannels(ch); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())

out = OUT / args.out
subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-framerate", str(args.fps), "-i", str(frames / "%05d.jpg"),
                "-i", str(wav_out), "-vf", "scale=in_range=jpeg:out_range=tv,format=yuv420p", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)], check=True)
print(f"done: {out}  ({out.stat().st_size / 1e6:.1f} MB, {time.time() - t_start:.0f}s)")
