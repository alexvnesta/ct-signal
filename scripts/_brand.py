"""The brand recipe for script-generated artifacts (covers, icons, digest).

Palette mirrors theme.py's CSS variables; fonts fall back to the DejaVu set
that ships with the GitHub ubuntu runners, so CI and local runs agree.
One file to change when the brand changes — not four.
"""
from __future__ import annotations

import os
import sys

from PIL import ImageFont

# RGB triples (canvas/panel art in covers and icons)
BG2 = (10, 15, 20)
PANEL = (21, 29, 39)
LINE = (40, 57, 74)
INK = (233, 238, 244)
DIM = (147, 167, 185)
ACC = (242, 166, 90)
OK = (143, 214, 169)

# CSS-identical hexes for HTML-ish outputs (digest email)
H_BG, H_PANEL, H_LINE = "#0e141b", "#151d27", "#28394a"
H_INK, H_DIM, H_ACC, H_OK = "#e9eef4", "#93a7b9", "#f2a65a", "#8fd6a9"

SITE = (os.environ.get("SITE_URL") or "https://ctsignal.org").rstrip("/")

if sys.platform == "darwin":
    SANS = "/System/Library/Fonts/Helvetica.ttc"      # idx 0 reg, 1 bold
    SERIF = "/System/Library/Fonts/Supplemental/Georgia.ttf"
    BOLD = SANS
else:  # GitHub-hosted runners
    SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
    BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(path: str, size: int, index: int = 0):
    if index and path == SANS and sys.platform != "darwin":
        path, index = BOLD, 0   # DejaVu bold is a file, not a ttc face
    try:
        return ImageFont.truetype(path, size, index=index)
    except OSError:  # font drift must never kill artifact generation
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
