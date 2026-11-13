"""Build a contact sheet PNG from a folder of thumbnails.
  python contact-sheet.py [folder] [output.png]
Defaults to scripts/out/preview -> scripts/out/contact-sheet.png
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
folder = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "out" / "preview"
dest = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "out" / "contact-sheet.png"
dest.parent.mkdir(parents=True, exist_ok=True)

files = sorted(folder.glob("*.webp"))
cols, pad, label = 6, 8, 16
cw = max(Image.open(f).width for f in files)
ch = max(Image.open(f).height for f in files)
rows = -(-len(files) // cols)
sheet = Image.new("RGB", (cols * (cw + pad) + pad, rows * (ch + label + pad) + pad), "#222")
d = ImageDraw.Draw(sheet)
for i, f in enumerate(files):
    x = pad + (i % cols) * (cw + pad)
    y = pad + (i // cols) * (ch + label + pad)
    sheet.paste(Image.open(f).convert("RGB"), (x, y))
    d.text((x, y + ch + 2), f.stem[:28], fill="#ddd")
sheet.save(dest)
print(f"{len(files)} thumbnails -> {dest}")
