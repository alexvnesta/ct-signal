"""Per-town share cards: five numbers a resident would actually forward.

One PNG per town, 1200x630, drawn from data/towns.json via towns.briefs()
— the same numbers, ranks, denominators and vintage the town file shows,
so a shared card can never disagree with the page it came from.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from PIL import Image, ImageDraw  # noqa: E402
from _brand import BG2, PANEL, LINE, INK, DIM, ACC, SITE, font, wrap  # noqa: E402
from ctsignal import towns  # noqa: E402

W, H = 1200, 630
SERIF_T = font(__import__("_brand").SERIF, 64)
BOLD = font(__import__("_brand").SANS, 30, 1)
VAL = font(__import__("_brand").SANS, 38, 1)
CAP = font(__import__("_brand").SANS, 21)
RANK = font(__import__("_brand").SANS, 21, 1)
SMALL = font(__import__("_brand").SANS, 22)
FIVE = [("income", "Median household income"), ("poverty", "Below poverty line"),
        ("rent", "Median gross rent"), ("value", "Median home value"),
        ("age", "Median age")]
IDX = {"income": 2, "poverty": 3, "rent": 4, "value": 5, "age": 1}


def fmt(key: str, v) -> str:
    if v is None:
        return "\u2014"
    if key == "poverty":
        return f"{v:.1f}%"
    if key == "age":
        return str(round(v))
    if key == "pop":
        return f"{v:,.0f}"
    return f"${v:,.0f}"


def cover(slug: str, t: dict, n: dict, vintage: str) -> Image.Image:
    img = Image.new("RGB", (W, H), BG2)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 76], fill=PANEL)
    d.text((48, 24), "CT", font=BOLD, fill=INK)
    d.text((48 + d.textlength("CT", font=BOLD) + 12, 24), "Signal",
           font=BOLD, fill=ACC)
    d.text((W - 48 - d.textlength(SITE.replace("https://", ""), font=SMALL),
            28), SITE.replace("https://", ""), font=SMALL, fill=DIM)
    d.text((48, 108), t["n"], font=SERIF_T, fill=INK)
    v = t["v"]
    pop = fmt("pop", v[0][0])
    sub = f"Connecticut \u00b7 {vintage} \u00b7 population {pop}"
    d.text((48, 190), sub, font=CAP, fill=DIM)
    bw, gap, x0, y0 = 212, 12, 48, 250
    for i, (key, label) in enumerate(FIVE):
        x = x0 + i * (bw + gap)
        d.rectangle([x, y0, x + bw, y0 + 210], fill=PANEL, outline=LINE)
        val, rank = v[IDX[key]]
        lines = wrap(d, fmt(key, val), VAL, bw - 28)
        for j, line in enumerate(lines[:2]):
            d.text((x + 14, y0 + 22 + j * 44), line, font=VAL, fill=INK)
        rk = ("\u2014" if rank is None
              else f"#{rank} of {n.get(key, '?')} in state")
        d.text((x + 14, y0 + 128), rk, font=RANK, fill=ACC)
        for j, line in enumerate(wrap(d, label, CAP, bw - 28)[:2]):
            d.text((x + 14, y0 + 158 + j * 24), line, font=CAP, fill=DIM)
    d.text((48, H - 58), "Know where you live. Every number names its "
           "source and vintage \u00b7 ctsignal.org", font=CAP, fill=DIM)
    return img


def main() -> int:
    b = towns.briefs()
    if not b:
        print("no towns data"); return 1
    out = 0
    for slug, t in b["towns"].items():
        img = cover(slug, t, b["n"], b["vintage"])
        dst = Path(__file__).resolve().parent.parent / "assets" / f"town-{slug}.png"
        img.save(dst, optimize=True)
        out += 1
    print(f"drew {out} town share cards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
