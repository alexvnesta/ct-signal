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

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
OUT.mkdir(exist_ok=True)

import sys as _sys
_sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _brand import BG2, PANEL, LINE, INK, DIM, ACC, OK, SANS, SERIF, font, SITE, wrap



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
    import datetime as _dt
    from zoneinfo import ZoneInfo
    _d = _dt.datetime.fromisoformat(card["generated_at"]).astimezone(
        ZoneInfo("America/New_York"))
    stamp = f"{_d:%b %-d, %Y %-I:%M %p} ET"
    d.text((W - 60 - d.textlength(stamp, font=ft), 574), stamp, font=ft,
           fill=DIM)
    return img


def thumb(card: dict) -> Image.Image | None:
    """Board-card thumbnail: the shape of the answer, no sentences. The card
    itself carries kicker/question/answer; text inside the art just repeated
    them at unreadable size. What can't be repeated is the picture: every
    peer as a bar, Connecticut in orange, the number as art."""
    rows = [r for r in ((card.get("chart") or {}).get("data") or {})
            .get("values", []) if "value" in r and "rank" in r]
    if len(rows) < 2:
        return None
    rows.sort(key=lambda r: r["rank"])
    W, H = 1200, 600
    img = Image.new("RGB", (W, H), BG2)
    d = ImageDraw.Draw(img)
    ans = card["answer_text"]
    av = card.get("answer_values") or {}
    if card.get("stream") == "local" and isinstance(av.get("top"), dict):
        val_txt = f"+{av['top']['pct']:.1f}%"
    elif "$" in ans:
        val_txt = f"${float(av.get('value', 0)):,.0f}"
    elif "%" in ans:
        val_txt = f"{float(av.get('value', 0)):g}%"
    else:
        val_txt = f"{float(av.get('value', 0)):,.0f}"
    fsize = 150
    while fsize > 60 and d.textlength(val_txt, font=font(SANS, fsize, 1)) > 430:
        fsize -= 10
    d.text((56, 210), val_txt, font=font(SANS, fsize, 1), fill=INK)
    n = av.get("n") or len(rows)
    d.text((58, 210 + fsize + 14), f"across {n} peers",
           font=font(SANS, 24), fill=DIM)

    # mini ranking: every peer as a bar, drawn in rank order — the same
    # shape as the story's chart, so the picture and the data agree.
    bar_lo, bar_hi, base, ceil_ = 520, 1140, 524, 150
    step = (bar_hi - bar_lo) / len(rows)
    bw = max(6, min(46, step * 0.66))
    lo = min(r["value"] for r in rows)
    hi = max(r["value"] for r in rows)
    span = (hi - lo) or 1.0
    dim_bar = (40, 52, 66)
    for i, r in enumerate(rows):
        h = 14 + int((base - ceil_) * 0 + (base - ceil_) * (r["value"] - lo) / span)
        x0 = bar_lo + i * step
        d.rectangle((x0, base - h, x0 + bw, base),
                    fill=ACC if r.get("highlight") else dim_bar)
    d.line((bar_lo - 16, base + 1, bar_hi, base + 1), fill=LINE, width=2)

    bolt(d, 56, 540, 26, ACC)
    d.text((92, 542), SITE.replace("https://", ""), font=font(SANS, 21, 1),
           fill=ACC)
    return img


if __name__ == "__main__":
    feed = json.loads((ROOT / "output/cards.json").read_text())
    for c in feed["cards"]:
        path = OUT / f"story-{c['id']}.png"
        cover(c).save(path, optimize=True)
        print("wrote", path.name)
        t = thumb(c)
        if t is not None:
            tpath = OUT / f"story-{c['id']}-thumb.png"
            t.save(tpath, optimize=True)
            print("wrote", tpath.name)
