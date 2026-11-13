"""Crop duck cards and write WebP thumbnails + manifest.

Reads originals only; never modifies them.
  python process-ducks.py --sample 12   # preview set -> scripts/out/preview/
  python process-ducks.py               # full run   -> assets/duck-thumbnails/
Crop values (pixels trimmed from each edge) live in crop.json, with optional
per-card overrides keyed by file stem, e.g. "D009_pirate": {"top": 60}.
"""
import argparse, json
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0, help="process N evenly spaced cards into scripts/out/preview")
    args = ap.parse_args()

    cfg = json.loads((HERE / "crop.json").read_text())
    local = HERE / "crop.local.json"   # machine-specific overrides, not committed
    if local.exists():
        cfg.update(json.loads(local.read_text()))
    src = Path(cfg["source_dir"])
    files = sorted(p for p in src.iterdir() if p.suffix.lower() == ".png")
    files = [p for p in files if p.stem.split("_")[0] not in cfg["exclude_ids"]]

    if args.sample:
        step = max(1, len(files) // args.sample)
        files = files[::step][: args.sample]
        out = HERE / "out" / "preview"
    else:
        out = ROOT / "assets" / "duck-thumbnails"
    out.mkdir(parents=True, exist_ok=True)

    manifest = []
    for p in files:
        c = {**cfg["crop"], **cfg["overrides"].get(p.stem, {})}
        with Image.open(p) as im:
            im = im.convert("RGB")
            if list(im.size) != cfg["expected_size"]:
                print(f"WARNING {p.name}: size {im.size}, expected {cfg['expected_size']}")
            w, h = im.size
            box = (c["left"], c["top"], w - c["right"], h - c["bottom"])
            tile = im.crop(box)
            tw = cfg["thumb_width"]
            th = round(tile.height * tw / tile.width)  # keep aspect ratio
            tile = tile.resize((tw, th), Image.LANCZOS)
            name = p.stem + ".webp"
            tile.save(out / name, "WEBP", quality=cfg["webp_quality"], method=6)
            manifest.append({"file": name, "id": p.stem.split("_")[0], "w": tw, "h": th})

    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"{len(manifest)} thumbnails -> {out}")


if __name__ == "__main__":
    main()
