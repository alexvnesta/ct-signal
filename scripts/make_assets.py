"""One-shot brand asset generator (run with the Pillow-enabled interpreter).

Produces assets/favicon.svg, assets/favicon-32.png, assets/apple-touch-icon.png
and assets/og-cover.png (1200×630 — the size every social crawler wants).
Design language mirrors site.css: same palette, same voice.
"""
from __future__ import annotations

import pathlib

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
OUT.mkdir(exist_ok=True)

import sys as _sys
_sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import os

from _brand import BG2, PANEL, LINE, INK, DIM, ACC, OK, SANS, SERIF, font
from _kit import dot_map, duotone, scrim, SRC

BG = (14, 20, 27)          # --bg (icon field only; see _brand for the rest)


def rounded(draw, box, r, fill):
    draw.rounded_rectangle(box, radius=r, fill=fill)


def bolt(draw, x, y, s, color):
    """Lightning bolt inside (x, y, s), s = box size."""
    pts = [(0.62, 0.02), (0.10, 0.56), (0.42, 0.56), (0.30, 0.98),
           (0.90, 0.40), (0.55, 0.40)]
    draw.polygon([(x + px * s, y + py * s) for px, py in pts], fill=color)


def brand(draw, x, y, size):
    """CT⚡Signal wordmark, returns width consumed."""
    f = font(SANS, size, 1)
    w_ct = draw.textlength("CT", font=f)
    w_sig = draw.textlength("Signal", font=f)
    gap = size * 0.10
    bolt_s = size * 1.02
    draw.text((x, y), "CT", font=f, fill=INK)
    bolt(draw, x + w_ct + gap, y - size * 0.02, bolt_s, ACC)
    draw.text((x + w_ct + gap + bolt_s + gap, y), "Signal", font=f, fill=ACC)
    return w_ct + gap + bolt_s + gap + w_sig


def _og_flat():
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), BG2)
    d = ImageDraw.Draw(img)

    # layered panels right side — abstract "board" motif
    rounded(d, (700, 70, 1150, 300), 18, PANEL)
    rounded(d, (700, 330, 1150, 560), 18, PANEL)
    d.text((740, 110), "Median gross rent", font=font(SANS, 26), fill=DIM)
    d.text((740, 148), "$1,488", font=font(SANS, 64, 1), fill=OK)
    rounded(d, (740, 236, 1010, 272), 18, (26, 36, 48))
    d.text((760, 242), "#17 of 52 peers · data 2024", font=font(SANS, 22),
           fill=(207, 220, 234))
    # dot strip = "we rank among 52"
    n = 52
    top = 430
    for i in range(n):
        cx = 740 + i * (370 / n)
        ct = i == 16
        r = 7 if ct else 5
        c = ACC if ct else (90, 110, 128)
        d.ellipse((cx - r, top - r, cx + r, top + r), fill=c)
    d.text((740, 470), "Connecticut highlighted", font=font(SANS, 22), fill=DIM)

    # left column — masthead + promise
    brand(d, 60, 90, 72)
    d.line((60, 205, 620, 205), fill=LINE, width=2)
    d.text((60, 235), "Connecticut's automated data desk",
           font=font(SANS, 34, 1), fill=INK)
    d.text((60, 292), "The news cycle picks the question.", font=font(SERIF, 30),
           fill=DIM)
    d.text((60, 336), "Public data answers it —", font=font(SERIF, 30), fill=DIM)
    d.text((60, 380), "with the receipts attached.", font=font(SERIF, 30), fill=DIM)
    rounded(d, (60, 452, 560, 500), 14, PANEL)
    d.text((80, 462), "Know where you live.",
           font=font(SANS, 24), fill=OK)
    d.text((60, 552), "ctsignal.org", font=font(SANS, 30, 1), fill=ACC)
    img.save(OUT / "og-cover.png", optimize=True)


def og_cover():
    # Social card: generated hero, duotoned; CT dot-map from real geometry.
    # Falls back to the flat vector build when the art sources are absent.
    hero = os.path.join(SRC, "hero-waveform.webp")
    try:
        img = duotone(hero, 1200, 630, BG2, ACC).convert("RGBA")
        mark = dot_map(500, None, ACC, grid=LINE)
        img.paste(mark, (1200 - mark.width - 56, (630 - mark.height) // 2 + 30), mark)
        scrim(img, (46, 196, 830, 420), BG, 110)
        d = ImageDraw.Draw(img)
        brand(d, 70, 215, 112)
        d.text((72, 372), "Know where you live.  ·  ctsignal.org",
               font=font(SANS, 30), fill=DIM)
        d.line((70, 588, 420, 588), fill=ACC, width=3)
        img.convert("RGB").save(OUT / "og-cover.png", optimize=True)
    except (OSError, ValueError):
        _og_flat()


def digest_header():
    # Header band for the weekly email: contour weave, inverted to brand colours.
    src = os.path.join(SRC, "hero-contours.webp")
    try:
        img = duotone(src, 1200, 260, BG, ACC, gamma=0.9, invert=True).convert("RGBA")
        mark = dot_map(230, None, ACC, grid=None)
        img.paste(mark, (1200 - mark.width - 60, (260 - mark.height) // 2), mark)
        scrim(img, (46, 36, 660, 224), BG, 120)
        d = ImageDraw.Draw(img)
        brand(d, 70, 66, 86)
        d.text((72, 190), "The weekly digest  ·  filed weekly, sent by a human",
               font=font(SANS, 24), fill=DIM)
        img.convert("RGB").save(OUT / "digest-header.png", optimize=True)
    except (OSError, ValueError):
        pass  # emails simply render without the band



def favicon_png(size, path):
    img = Image.new("RGBA", (size, size), BG)
    d = ImageDraw.Draw(img)
    rounded(d, (0, 0, size - 1, size - 1), size * 0.18, BG2)
    s = size * 0.52
    # CT
    f = font(SANS, int(size * 0.44), 1)
    d.text((size * 0.12, size * 0.30), "CT", font=f, fill=INK)
    bolt(d, size * 0.60, size * 0.24, s, ACC)
    img.save(path)


def favicon_svg():
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="12" fill="#0a0f14"/>
<text x="7" y="44" font-family="Helvetica,Arial,sans-serif" font-weight="bold"
font-size="28" fill="#e9eef4">CT</text>
<polygon points="51.5,8.3 30,38 40.5,38 35.5,58 57,26.5 46,26.5" fill="#f2a65a"/>
</svg>
'''
    (OUT / "favicon.svg").write_text(svg)


if __name__ == "__main__":
    og_cover()
    digest_header()
    favicon_png(32, OUT / "favicon-32.png")
    favicon_png(192, OUT / "icon-192.png")
    favicon_png(512, OUT / "icon-512.png")
    # maskable: brand glyph shrunk into the safe zone on a solid field
    m = Image.new("RGB", (512, 512), BG2)
    md = ImageDraw.Draw(m)
    rounded(md, (46, 46, 466, 466), 96, PANEL)
    # the icon glyph (CT + bolt), not the wordmark: "Signal" overflowed the
    # 512 safe zone and vanished, leaving a mark that matched nothing else
    f = font(SANS, 512 * 0.34, 1)
    md.text((512 * 0.14, 512 * 0.31), "CT", font=f, fill=INK)
    bolt(md, 512 * 0.62, 512 * 0.25, 512 * 0.40, ACC)
    m.save(OUT / "icon-maskable-512.png", optimize=True)
    favicon_png(180, OUT / "apple-touch-icon.png")
    favicon_svg()
    print("assets written:", sorted(p.name for p in OUT.iterdir()))
