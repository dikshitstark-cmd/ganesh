"""
generate_placeholders.py
Run once (python generate_placeholders.py) to create simple placeholder
images in static/images/ so the receipt template always has something to
show. Replace these files with real Ganesh artwork any time you like --
same filenames, same folder, nothing else needs to change.
"""

from pathlib import Path
from PIL import Image, ImageDraw

IMG_DIR = Path(__file__).resolve().parent / "static" / "images"
IMG_DIR.mkdir(parents=True, exist_ok=True)


def make_emblem(path, size=200, fg=(255, 140, 0), bg=(255, 255, 255, 0)):
    """A simple round saffron emblem with a lotus-like motif as a stand-in
    for a Ganesh idol image."""
    img = Image.new("RGBA", (size, size), bg)
    d = ImageDraw.Draw(img)
    c = size // 2
    r = int(size * 0.46)
    d.ellipse([c - r, c - r, c + r, c + r], outline=fg, width=6)
    # petal motif
    for i in range(8):
        import math
        ang = i * (360 / 8)
        x = c + int(r * 0.55 * math.cos(math.radians(ang)))
        y = c + int(r * 0.55 * math.sin(math.radians(ang)))
        pr = int(size * 0.09)
        d.ellipse([x - pr, y - pr, x + pr, y + pr], fill=fg)
    d.ellipse([c - r * 0.35, c - r * 0.35, c + r * 0.35, c + r * 0.35], fill=fg)
    img.save(path)


def make_watermark(path, size=800, fg=(255, 140, 0, 40)):
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    c = size // 2
    r = int(size * 0.42)
    d.ellipse([c - r, c - r, c + r, c + r], outline=fg, width=14)
    d.ellipse([c - r * 0.5, c - r * 0.5, c + r * 0.5, c + r * 0.5], fill=fg)
    img.save(path)


if __name__ == "__main__":
    make_emblem(IMG_DIR / "ganesh_left.png")
    make_emblem(IMG_DIR / "ganesh_right.png")
    make_watermark(IMG_DIR / "watermark.png")
    print("Placeholder images written to", IMG_DIR)
