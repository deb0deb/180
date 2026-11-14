// Duck finale engine.
// The audio element's currentTime is the master clock. events.json holds the
// choreography (when / how many); the duck cast is shuffled fresh each play.
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const stage = $("stage"), scene = $("scene"), mosaic = $("mosaic"), finale = $("finale");
  const opening = $("opening"), snd = $("snd"), startBtn = $("start"), soundBtn = $("sound"), replayBtn = $("replay");

  const CELLS = 12;          // 3 x 4
  const HOLD = 0.20;         // seconds a full mosaic stays up before clearing
  const LEAD = 0.04;         // reveal this many seconds ahead of the beat (feels snappier)
  const OPEN_MS = 2400;      // opening message time before music + iris
  const THUMBS = "assets/duck-thumbnails/";
  const SEED = 180;          // fixed: reveal POSITIONS repeat every play, ducks do not

  let manifest = [], cfg = null, deck = [], deckPos = 0, st = null, raf = 0, openTimer = 0;

  // ---- helpers ----
  function mulberry32(a) {
    return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  function shuffle(arr, rnd) {
    for (let i = arr.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [arr[i], arr[j]] = [arr[j], arr[i]]; }
    return arr;
  }
  const preload = (file) => { const im = new Image(); im.src = THUMBS + file; };

  // ---- cells ----
  const cells = [];
  for (let i = 0; i < CELLS; i++) {
    const c = document.createElement("div"); c.className = "cell";
    const im = document.createElement("img"); im.alt = ""; im.decoding = "async";
    c.appendChild(im); mosaic.appendChild(c); cells.push(c);
  }

  // ---- duck deck: no repeats until the inventory is used up, then reshuffle ----
  function takeDuck() {
    if (deckPos >= deck.length) { deck = shuffle(manifest.slice(), Math.random); deckPos = 0; }
    const d = deck[deckPos++];
    for (let k = 0; k < 12 && deckPos + k < deck.length; k++) preload(deck[deckPos + k].file);
    return d;
  }

  // ---- mosaic state ----
  function newMosaic() {
    st.mosaicIdx++;
    st.order = shuffle([...Array(CELLS).keys()], mulberry32(SEED + st.mosaicIdx));
    st.filled = 0; st.fullAt = null;
    cells.forEach((c) => c.classList.remove("on"));
  }

  // Reveal up to `count` ducks. If the mosaic has fewer empty cells, fill what
  // fits and queue the remainder for the next mosaic.
  function reveal(count, t) {
    const n = Math.min(count, CELLS - st.filled);
    for (let k = 0; k < n; k++) {
      const cell = cells[st.order[st.filled++]];
      cell.firstChild.src = THUMBS + takeDuck().file;
      cell.classList.add("on");
    }
    if (count > n) st.pending += count - n;
    if (st.filled >= CELLS && st.fullAt === null) st.fullAt = t;
  }

  // Little sparkle "twink" for the wink, synthesized (no audio file needed).
  let ac = null;
  function twink() {
    try {
      if (!ac) return;
      const t = ac.currentTime;
      [[1976, 0], [2637, 0.09], [3136, 0.18]].forEach(([f, d]) => {
        const o = ac.createOscillator(), v = ac.createGain();
        o.type = "sine"; o.frequency.value = f;
        v.gain.setValueAtTime(0.0001, t + d);
        v.gain.exponentialRampToValueAtTime(0.5, t + d + 0.01);
        v.gain.exponentialRampToValueAtTime(0.0001, t + d + 0.5);
        o.connect(v).connect(ac.destination); o.start(t + d); o.stop(t + d + 0.6);
      });
    } catch (e) { /* sound is a bonus; never break the animation */ }
  }

  function ensureAudio() {   // call from inside a tap so the browser allows it
    try {
      ac = ac || new (window.AudioContext || window.webkitAudioContext)();
      if (ac.state === "suspended") ac.resume();
    } catch (e) { ac = null; }
  }

  function doFinale() {
    st.finaleDone = true;
    const clone = mosaic.cloneNode(true);
    clone.removeAttribute("id");
    mosaic.classList.add("half-l");
    clone.classList.add("half-r");
    scene.appendChild(clone);
    st.clone = clone;
    finale.classList.add("show");
    const q = cfg.cues, add = (c) => () => finale.classList.add(c), rm = (c) => () => finale.classList.remove(c);
    st.cues = [
      { t: q.bunny, fn: add("f-bunny") }, { t: q.lettering, fn: add("f-text") },
      { t: q.line, fn: add("f-line") }, { t: q.wink, fn: () => { finale.classList.add("f-wink"); if (!st.seeking) twink(); } }, { t: q.winkEnd, fn: rm("f-wink") },
    ].sort((a, b) => a.t - b.t);
    st.cueI = 0;
    void mosaic.offsetWidth; // flush so the slide transition runs
    mosaic.classList.add("go"); clone.classList.add("go");
  }

  // ---- master loop ----
  function step(t) {
    const ev = cfg.events;
    while (st.i < ev.length && ev[st.i].time <= t + LEAD) {
      const e = ev[st.i++];
      if (st.finaleDone) continue;
      if (e.action === "reveal") {
        if (st.fullAt !== null) st.pending += e.count; else reveal(e.count, t);
      } else if (e.action === "nextMosaic") {
        if (st.filled > 0 && st.fullAt === null) st.fullAt = t;
      } else if (e.action === "finale") {
        doFinale();
      }
    }
    if (!st.finaleDone && st.fullAt !== null && t - st.fullAt >= HOLD) {
      const carry = st.pending; st.pending = 0;
      newMosaic();
      if (carry > 0) reveal(carry, t);
    }
    while (st.finaleDone && st.cueI < st.cues.length && st.cues[st.cueI].t <= t) st.cues[st.cueI++].fn();
    if (!st.iris && t >= cfg.iris_start) { st.iris = true; scene.classList.add("iris"); }
  }

  function tick() {
    const t = snd.currentTime;
    step(t);
    if (window.duck && window.duck.onTick) window.duck.onTick(t);
    if (!snd.ended) raf = requestAnimationFrame(tick);
  }

  // Jump anywhere: rebuild state by fast-forwarding the choreography to t.
  function seek(target) {
    ensureAudio();
    cancelAnimationFrame(raf);
    resetVisuals();
    startBtn.hidden = true; replayBtn.hidden = true; soundBtn.hidden = true;
    scene.classList.add("open");
    scene.style.animationDuration = "0s";
    st.seeking = true;
    for (let tt = 0; tt <= target; tt += 0.03) step(tt);
    st.seeking = false;
    snd.muted = false;
    snd.currentTime = target;
    snd.play().then(() => { raf = requestAnimationFrame(tick); }).catch(() => { soundBtn.hidden = false; });
  }

  // ?debug loads js/debug.local.js (a local-only file, not in the repo) which adds
  // a scrub bar. Without that file, ?debug does nothing.
  let dbg = null;
  function initDebug() {
    if (!/[?&]debug/.test(location.search)) return;
    window.duck = { seek, twink, ensureAudio, cfg, snd, onTick: null };
    const s = document.createElement("script");
    s.src = "js/debug.local.js";
    document.body.appendChild(s);
  }

  function resetVisuals() {
    cancelAnimationFrame(raf);
    clearTimeout(openTimer);
    opening.className = "";
    mosaic.className = "mosaic";
    if (st && st.clone) st.clone.remove();
    finale.className = ""; scene.className = ""; scene.style.animationDuration = "";
    void scene.offsetWidth;
    cells.forEach((c) => c.classList.remove("on"));
    st = { i: 0, mosaicIdx: 0, order: [], filled: 0, fullAt: null, pending: 0,
           finaleDone: false, cues: [], cueI: 0, iris: false, clone: null, seeking: false };
    newMosaic();
  }

  function run() {
    resetVisuals();
    startBtn.hidden = true; replayBtn.hidden = true; soundBtn.hidden = true;
    // Opening message on black, silent. Unlock audio inside this tap so the
    // delayed play() below is allowed by mobile browsers.
    ensureAudio();
    snd.muted = true;
    snd.play().then(() => { snd.pause(); snd.currentTime = 0; snd.muted = false; })
              .catch(() => { snd.muted = false; });
    opening.classList.add("show");
    clearTimeout(openTimer);
    openTimer = setTimeout(startMusic, OPEN_MS);
  }

  function startMusic() {
    scene.classList.add("open");      // iris opens, ducks start with the music
    snd.currentTime = 0;
    snd.muted = false;
    snd.play().then(() => { raf = requestAnimationFrame(tick); })
              .catch(() => { soundBtn.hidden = false; });
  }

  startBtn.addEventListener("click", run);
  replayBtn.addEventListener("click", run);
  soundBtn.addEventListener("click", () => {
    snd.play().then(() => { soundBtn.hidden = true; raf = requestAnimationFrame(tick); })
              .catch(() => { soundBtn.textContent = "Sound unavailable"; });
  });
  snd.addEventListener("ended", () => { cancelAnimationFrame(raf); replayBtn.hidden = false; });
  snd.addEventListener("error", () => { soundBtn.hidden = false; });

  // ---- load choreography + cast ----
  startBtn.disabled = true;
  Promise.all([
    fetch("events.json").then((r) => r.json()),
    fetch(THUMBS + "manifest.json").then((r) => r.json()),
  ]).then(([events, files]) => {
    cfg = events; manifest = files;
    manifest.slice(0, 24).forEach((m) => preload(m.file));
    ["01-concentric-rings", "02-body", "03-head", "04-wink", "05-duck-on-hand", "06-lettering", "07-underline"]
      .forEach((n) => { new Image().src = "assets/finale/" + n + ".png"; });
    resetVisuals();
    startBtn.disabled = false;
    initDebug();
  }).catch((err) => { startBtn.textContent = "Could not load"; console.error(err); });
})();
