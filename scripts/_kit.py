"""Connecticut as a dot-grid mark, plus duotone treatment for the generated art.

Geometry: Natural Earth 10m admin-1 (public domain), see assets-src/README.md.
Art: generated on free community GPU inference (Stable Horde), see docs/LAUNCH.md.
"""
import json, math, os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "assets-src")

def ct_shape(w, poly=None):
    """Census/Natural-Earth outline scaled to width w at true aspect → (pts, h)."""
    ring = json.load(open(poly or os.path.join(HERE, "ct_poly.json")))
    k = math.cos(math.radians(41.5))          # shrink longitude for our latitude
    pts = [(lon * k, -lat) for lon, lat in ring]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    sx = w / (max(xs) - min(xs))
    return [((x - min(xs)) * sx, (y - min(ys)) * sx) for x, y in pts], (max(ys) - min(ys)) * sx

def dot_map(w, line, dots, grid=None, pitch=17, graticule=True):
    """Connecticut drawn as an amber dot grid on its own lat/long graticule."""
    pts, h = ct_shape(w)
    h = int(h)
    pad = pitch * 2
    cv = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(cv)
    shape = [(x + pad, y + pad) for x, y in pts]
    if graticule and grid:
        for gx in range(pad, w + pad, pitch):
            d.line([(gx, pad), (gx, h + pad)], grid + (90,), 1)
        for gy in range(pad, h + pad, pitch):
            d.line([(pad, gy), (w + pad, gy)], grid + (90,), 1)
    clip = Image.new("L", cv.size, 0)
    ImageDraw.Draw(clip).polygon(shape, fill=255)
    cp = clip.load()
    r = max(2, round(pitch * 0.29))
    for gy in range(pad + pitch // 2, h + pad, pitch):
        for gx in range(pad + pitch // 2, w + pad, pitch):
            if cp[gx, gy] > 128:
                d.ellipse([gx - r, gy - r, gx + r, gy + r], fill=dots + (255,))
    return cv

def duotone(path, w, h, dark, light, gamma=0.85, invert=False):
    """Cover-crop to w×h, stretch luminance p2–p98 across a two-colour ramp."""
    src = Image.open(path).convert("RGB")
    s = max(w / src.width, h / src.height)
    src = src.resize((round(src.width * s), round(src.height * s)), Image.LANCZOS)
    x, y = (src.width - w) // 2, (src.height - h) // 2
    src = src.crop((x, y, x + w, y + h)).convert("L")

    hist, tot = src.histogram(), sum(src.histogram())
    lo = hi = 0
    for cut, key in ((0.02, "lo"), (0.98, "hi")):
        cum = 0
        for i, n in enumerate(hist):
            cum += n
            if cum >= tot * cut:
                if key == "lo":
                    lo = i
                else:
                    hi = max(i, lo + 24)
                break
    span = max(1.0, hi - lo)
    ramp = []
    for i in range(256):
        t = min(1.0, max(0.0, (i - lo) / span)) ** gamma
        ramp.append(tuple(round(dark[c] + (light[c] - dark[c]) * (1 - t if invert else t))
                          for c in range(3)))
    return Image.merge("RGB", [src.point([ramp[i][c] for i in range(256)]) for c in range(3)])

def scrim(img, box, color, alpha=115):
    """Soft panel that keeps text legible over busy artwork."""
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).rounded_rectangle(box, radius=18, fill=tuple(color) + (alpha,))
    img.alpha_composite(ov)
