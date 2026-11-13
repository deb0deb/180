// Duck finale engine.
// The audio element's currentTime is the master clock. events.json holds the
// choreography (when / how many); the duck cast is shuffled fresh each play.
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const stage = $("stage"), scene = $("scene"), mosaic = $("mosaic"), finale = $("finale");
  const snd = $("snd"), startBtn = $("start"), soundBtn = $("sound"), replayBtn = $("replay");

  const CELLS = 12;          // 3 x 4
  const HOLD = 0.28;         // seconds a full mosaic stays up before clearing
  const THUMBS = "assets/duck-thumbnails/";
  const SEED = 180;          // fixed: reveal POSITIONS repeat every play, ducks do not

  let manifest = [], cfg = null, deck = [], deckPos = 0, st = null, raf = 0;

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

  function doFinale() {
    st.finaleDone = true;
    const clone = mosaic.cloneNode(true);
    clone.removeAttribute("id");
    mosaic.classList.add("half-l");
    clone.classList.add("half-r");
    scene.appendChild(clone);
    st.clone = clone;
    finale.classList.add("show");
    void mosaic.offsetWidth; // flush so the slide transition runs
    mosaic.classList.add("go"); clone.classList.add("go");
  }

  // ---- master loop ----
  function tick() {
    const t = snd.currentTime;
    const ev = cfg.events;
    while (st.i < ev.length && ev[st.i].time <= t) {
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
    if (!st.popped && st.finaleDone && t >= cfg.spoken_time) { st.popped = true; finale.classList.add("pop"); }
    if (!st.iris && t >= cfg.iris_start) { st.iris = true; scene.classList.add("iris"); }
    if (!snd.ended) raf = requestAnimationFrame(tick);
  }

  function resetVisuals() {
    cancelAnimationFrame(raf);
    mosaic.className = "mosaic";
    if (st && st.clone) st.clone.remove();
    finale.className = ""; scene.className = "";
    void scene.offsetWidth;
    cells.forEach((c) => c.classList.remove("on"));
    st = { i: 0, mosaicIdx: 0, order: [], filled: 0, fullAt: null, pending: 0,
           finaleDone: false, popped: false, iris: false, clone: null };
    newMosaic();
  }

  function run() {
    resetVisuals();
    startBtn.hidden = true; replayBtn.hidden = true; soundBtn.hidden = true;
    snd.currentTime = 0;
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
    resetVisuals();
    startBtn.disabled = false;
  }).catch((err) => { startBtn.textContent = "Could not load"; console.error(err); });
})();
