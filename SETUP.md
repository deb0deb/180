# Setting up this project on a new computer

This is the duck #180 finale: a static web page (GitHub Pages) plus a few Python scripts for adding ducks. The page itself needs nothing installed. Only the duck-processing scripts need Python.

## 1. One-time installs (Windows)
1. **Git** - https://git-scm.com/download/win (accept the defaults).
2. **Python 3.12** - https://www.python.org/downloads/ (tick "Add python.exe to PATH").
3. **Claude Code** (to work with Claude in a folder) - follow the install steps at https://claude.com/claude-code.
4. A GitHub login for the `deb0deb` account. The first `git push` opens a browser sign-in.

## 2. Get the project
```
git clone https://github.com/deb0deb/180.git
cd 180
```

## 3. Install the Python tools (one time, a few minutes)
```
python -m venv scripts/.venv
scripts\.venv\Scripts\python -m pip install -r scripts/requirements.txt
```
(The Python tools are only needed for processing ducks and making MP4s. They are not committed to git.)

## 4. Local-only files (not in git)
Copy these from the Dropbox `claude-resume-kit` folder:
- `scripts/crop.local.json` - tells the scripts where the duck originals live. **Edit `source_dir`** to match the Dropbox path on this computer.
- `js/debug.local.js` - the scrub bar (open the page with `?debug`). Optional.

## 5. Adding new ducks
1. Save the finished card (720 x 1020 PNG, no text) in the Dropbox folder `.../03_final/ducks no text/` named `D082_two-words.png` (D + three digits + underscore + lowercase words with hyphens).
2. Process: `scripts\.venv\Scripts\python scripts/process-ducks.py` (crop is 78 / 90 / 78 / 260 px, set in `scripts/crop.json`).
3. Look at a contact sheet if you like: `scripts\.venv\Scripts\python scripts/contact-sheet.py assets/duck-thumbnails scripts/out/all.png`.
4. Commit and push: `git add assets && git commit -m "Add ducks" && git push`. GitHub Pages updates in a minute or two.

## 6. Preview locally
```
python -m http.server 8000
```
Then open http://localhost:8000/ (add `?debug` for the scrub bar). On a phone on the same Wi-Fi use the computer's address, e.g. http://192.168.x.x:8000/.

## 7. Other scripts
- `scripts/build-events.py` - rebuilds `events.json` (reveal choreography, finale timing, the 80th-birthday hero card).
- `scripts/analyze-audio.py` - re-analyzes `audio.mp3` if the track ever changes (run before build-events).
- `scripts/render-video.py` - renders the page to an MP4 (needs the local server running).

## Things to remember
- The live address is https://deb0deb.github.io/180/ and **must not change** (printed QR code). Never rename the repo.
- The audio file is the original Warner Bros. recording. Decide on music rights/hosting before the card is printed.
- Card D180 and the template card D036 are excluded from the random mix (`scripts/crop.json`).
