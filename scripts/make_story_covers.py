"""Per-story OG covers: 1200×630 PNG per card, so every story shares a
distinct, on-brand preview instead of one generic cover.

Run with the Pillow-enabled interpreter after the feed changes:
  <runtime-python> scripts/make_story_covers.py
newsroom._story_og() only references these files if they exist on disk, so a
missing cover degrades to the generic one — never a 404.
"""
from __future__ import annotations

import json
import pathlib
import textwrap

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
OUT.mkdir(exist_ok=True)

BG2 = (10, 15, 20)
PANEL = (21, 29, 39)
LINE = (40, 57, 74)
INK = (233, 238, 244)
DIM = (147, 167, 185)
ACC = (242, 166, 90)
OK = (143, 214, 169)

import sys

if sys.platform == "darwin":
    SANS = "/System/Library/Fonts/Helvetica.ttc"      # idx 0 reg, 1 bold
    SERIF = "/System/Library/Fonts/Supplemental/Georgia.ttf"
else:  # GitHub-hosted runners: DejaVu ships with the ubuntu image
    SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
_BOLD = SANS.replace("DejaVuSans", "DejaVuSans-Bold") if sys.platform != "darwin" else SANS


def font(path, size, index=0):
    if index and path == SANS and sys.platform != "darwin":
        path, index = _BOLD, 0   # DejaVu bold is a separate file, not a ttc face
    try:
        return ImageFont.truetype(path, size, index=index)
    except OSError:  # platform font drift must not kill a cover run
        return ImageFont.load_default(size)


def wrap(draw, text, f, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=f) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def bolt(draw, x, y, s, color):
    pts = [(0.62, 0.02), (0.10, 0.56), (0.42, 0.56), (0.30, 0.98),
           (0.90, 0.40), (0.55, 0.40)]
    draw.polygon([(x + px * s, y + py * s) for px, py in pts], fill=color)


def cover(card: dict) -> Image.Image:
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), BG2)
    d = ImageDraw.Draw(img)

    # mini masthead
    f = font(SANS, 34, 1)
    d.text((60, 48), "CT", font=f, fill=INK)
    bolt(d, 60 + d.textlength("CT", font=f) + 8, 46, 40, ACC)
    d.text((60 + d.textlength("CT", font=f) + 8 + 44 + 8, 48), "Signal",
           font=f, fill=ACC)
    ft = font(SANS, 17)
    kicker = (f'{card.get("topic", "")} · {card.get("stream", "")} desk'
              .upper())
    d.text((W - 60 - d.textlength(kicker, font=ft), 58), kicker, font=ft,
           fill=ACC)
    d.line((60, 118, W - 60, 118), fill=LINE, width=2)

    # question (serif, wrapped)
    fq = font(SERIF, 47)
    lines = wrap(d, card["question"], fq, W - 120)
    y = 150
    for ln in lines[:4]:
        d.text((60, y), ln, font=fq, fill=INK)
        y += 58

    # answer pill
    fa = font(SANS, 26, 1)
    alines = wrap(d, card["answer_text"], fa, W - 160)[:2]
    box_h = 26 + 38 * len(alines)
    d.rounded_rectangle((60, 430, 940, 430 + box_h), radius=14, fill=PANEL)
    d.rectangle((60, 430, 65, 430 + box_h), fill=OK)
    yy = 443
    for ln in alines:
        d.text((84, yy), ln, font=fa, fill=OK)
        yy += 38

    d.text((60, 570), "ctsignal.org", font=font(SANS, 24, 1), fill=ACC)
    stamp = card["generated_at"][:16].replace("T", " ") + " UTC"
    d.text((W - 60 - d.textlength(stamp, font=ft), 574), stamp, font=ft,
           fill=DIM)
    return img


if __name__ == "__main__":
    feed = json.loads((ROOT / "output/feed.json").read_text())
    for c in feed["cards"]:
        path = OUT / f"story-{c['id']}.png"
        cover(c).save(path, optimize=True)
        print("wrote", path.name)
