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
import _skyline as SKY

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
    # Social card: the Hartford skyline, drawn to scale (see _skyline.py).
    # Replaced the diffusion hero on purpose — the old one was a generic
    # city with an unreadable signature; this one is our city, and its
    # heights are real data with a citation.
    img = Image.new("RGB", (1200, 630), BG2)
    d = ImageDraw.Draw(img)
    SKY.draw(d, 0, 1200, 630, 260 / SKY.HEIGHT_FT_MAX, ACC)
    brand(d, 70, 70, 96)
    d.line((70, 210, 420, 210), fill=LINE, width=2)
    d.text((72, 240), "Know where you live.  ·  ctsignal.org",
           font=font(SANS, 30), fill=DIM)
    d.text((72, 292), "An automated newsroom. Every answer names its source.",
           font=font(SANS, 22), fill=OK)
    img.save(OUT / "og-cover.png", optimize=True)


def masthead():
    # Site nameplate band: Hartford at scale, the tallest building in
    # Connecticut clearing the brand panel. The board opens like a paper.
    img = Image.new("RGBA", (1200, 200), BG2)
    d = ImageDraw.Draw(img)
    SKY.draw(d, 0, 1200, 200, 150 / SKY.HEIGHT_FT_MAX, ACC)
    scrim(img, (30, 22, 640, 178), (10, 15, 20), 150)
    d = ImageDraw.Draw(img)
    brand(d, 56, 36, 68)
    d.text((58, 138), "Know where you live.  ·  public data, receipts attached",
           font=font(SANS, 22), fill=DIM)
    img.convert("RGB").save(OUT / "masthead.png", optimize=True)


def digest_header():
    # Email band: same skyline, taller frame, the digest's own line.
    img = Image.new("RGBA", (1200, 260), BG2)
    d = ImageDraw.Draw(img)
    SKY.draw(d, 0, 1200, 260, 190 / SKY.HEIGHT_FT_MAX, ACC)
    scrim(img, (30, 26, 640, 234), (10, 15, 20), 150)
    d = ImageDraw.Draw(img)
    brand(d, 56, 52, 82)
    d.text((58, 182), "The weekly digest  ·  filed weekly, sent by a human",
           font=font(SANS, 24), fill=DIM)
    img.convert("RGB").save(OUT / "digest-header.png", optimize=True)


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
    masthead()
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
