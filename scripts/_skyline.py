"""Hartford skyline, drawn to scale from public records.

Not a stock silhouette: every tower here is a real building at its listed
height, so the art is a chart of something. Heights (feet) and floor counts
from Wikipedia's "List of tallest buildings in Hartford" (CC BY-SA 4.0).
Left-to-right order follows the view from the Connecticut River — the way
the city is actually photographed: far ridge, then downtown, then the low
historic row along the ground.

Deliberately EXCLUDED: the tower Wikipedia's table lists as "Travelers
Tower" at 527 ft — the row's date (1919) and the article's own prose (2024)
contradict each other, so until the height is independently confirmed it
gets no pixels. An uncertain number is worse than a missing one.

The lit-window pattern is seeded per building name, so two renders are
identical: the art is a pure function of the inputs, not of the clock.
"""
from PIL import ImageDraw

# Layer, name, height_ft, floors, width (design units), style
# styles: flat | step | antenna | chamfer | spire | cupola | dome
FAR, MID, NEAR = 0, 1, 2
BUILDINGS = [
    (FAR, "Park River ridge", 130, 0, 1400, "flat"),

    (MID, "100 Constitution Plaza", 218, 18, 70, "flat"),
    (MID, "Bushnell Tower", 263, 28, 64, "flat"),
    (MID, "One Financial Plaza", 335, 26, 78, "flat"),      # "the Gold Building"
    (MID, "City Place I", 535, 38, 118, "step"),
    (MID, "Hartford Plaza", 334, 22, 62, "flat"),
    (MID, "280 Trumbull Street", 349, 28, 58, "flat"),
    (MID, "Goodwin Square", 522, 30, 74, "antenna"),
    (MID, "Hartford 21", 440, 36, 56, "chamfer"),
    (MID, "777 Main Street", 360, 26, 68, "flat"),
    (MID, "2 Park Place", 309, 25, 46, "flat"),
    (MID, "24 Park Place", 309, 25, 46, "flat"),

    (NEAR, "Old State House", 110, 0, 150, "cupola"),        # 1796
    (NEAR, "Center Church", 154, 0, 60, "spire"),            # white steeple, 1807
    (NEAR, "The Egg", 70, 0, 180, "dome"),                   # 1972, as the oval
]

HEIGHT_FT_MAX = 535.0   # City Place I: tallest building in Connecticut

# horizontal placement, as a share of the band width (river view, left→right)
X = {"Park River ridge": 0.00, "100 Constitution Plaza": 0.10,
     "Bushnell Tower": 0.185, "One Financial Plaza": 0.27,
     "City Place I": 0.37, "Hartford Plaza": 0.50,
     "280 Trumbull Street": 0.575, "Goodwin Square": 0.645,
     "Hartford 21": 0.735, "777 Main Street": 0.805,
     "2 Park Place": 0.885, "24 Park Place": 0.935,
     "Old State House": 0.03, "Center Church": 0.46, "The Egg": 0.72}

# depth reads through tone: far is closest to the sky, near is darkest
TONE = {FAR: (30, 41, 53), MID: (21, 29, 39), NEAR: (17, 24, 32)}
EDGE = {FAR: (48, 66, 84), MID: (58, 80, 100), NEAR: (72, 98, 122)}
LIT = {FAR: 0.012, MID: 0.075, NEAR: 0.030}


def _poly(d, pts, fill):
    d.polygon(pts, fill=fill)


def _windows(d, x, top, w, h, floors, rng, lit, body, glow, warm=None):
    if not floors or h < 30 or w < 12:
        return
    cols = max(2, int(w // 8))
    rows = min(floors, max(3, int(h // 7)))
    for r in range(rows):
        for c in range(cols):
            wx = x + 4 + c * (w - 8) / cols
            wy = top + 5 + r * (h - 10) / rows
            if rng.random() < lit:
                hot = warm and rng.random() < 0.12
                d.rectangle((wx, wy, wx + 2, wy + 2),
                            fill=warm if hot else glow)


def draw(d: ImageDraw.ImageDraw, x0: int, width: int, base: int,
         px_per_ft: float, acc=None) -> None:
    """Draw the skyline sitting on baseline `base`, scaled by px_per_ft.

    `acc` (brand orange) draws the horizon line — the one warm edge the
    band needs. Windows are seeded per building, never time-dependent.
    """
    import random
    for layer in (FAR, MID, NEAR):
        body, edge, lit = TONE[layer], EDGE[layer], LIT[layer]
        wu_total = sum(b[4] for b in BUILDINGS if b[0] == layer)
        for _, name, ft, floors, wu, style in BUILDINGS:
            if _layer_of(name) != layer:
                continue
            w = max(8, width * wu / wu_total * 0.62)
            h = max(8, int(ft * px_per_ft))
            x = x0 + width * X[name]
            top = base - h
            d.rectangle((x, top, x + w, base), fill=body)
            rng = random.Random(name)
            if style == "step":
                ins = w * 0.16
                d.rectangle((x + ins, top - h * 0.05, x + w - ins, top),
                            fill=body)
            elif style == "antenna":
                d.line((x + w / 2, top - h * 0.10, x + w / 2, top),
                       fill=edge, width=2)
            elif style == "chamfer":
                cut = min(w * 0.35, h * 0.08)
                _poly(d, [(x, top), (x + w - cut, top), (x + w, top + cut),
                          (x + w, base), (x, base)], body)
            elif style == "spire":
                d.rectangle((x, top + h * 0.42, x + w, base), fill=body)
                _poly(d, [(x - w * 0.06, top + h * 0.42),
                          (x + w * 1.06, top + h * 0.42),
                          (x + w / 2, top - h * 0.30)], body)
                d.line((x + w / 2, top - h * 0.30, x + w / 2,
                        top - h * 0.38), fill=edge, width=2)
            elif style == "cupola":
                d.rectangle((x, top + h * 0.30, x + w, base), fill=body)
                cx, cw = x + w / 2, w * 0.17
                d.rectangle((cx - cw, top - h * 0.10, cx + cw, top + h * 0.30),
                            fill=body)
                _poly(d, [(cx - cw * 1.2, top - h * 0.10),
                          (cx + cw * 1.2, top - h * 0.10),
                          (cx, top - h * 0.28)], body)
            elif style == "dome":
                d.chord((x, top, x + w, top + h * 1.9), 180, 360, fill=body)
                d.rectangle((x, top + h * 0.72, x + w, base), fill=body)
            _windows(d, x, top, w, h, floors, rng, lit, body, edge,
                     warm=acc)
            # sunward edge: one brighter line on the right face
            d.line((x + w - 1, top, x + w - 1, base), fill=edge, width=1)
    if acc:
        d.line((x0, base - 1, x0 + width, base - 1), fill=acc, width=2)


def _layer_of(name: str) -> int:
    return next(b[0] for b in BUILDINGS if b[1] == name)
