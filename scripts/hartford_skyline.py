"""Hartford, CT skyline silhouette — generates layered SVG vectors.

Every building is built from shapely polygons; windows are boolean-subtracted
so they are real transparent holes, and the back layer is knocked out under
the front layer (no overlapping shapes — clean for print, vinyl or laser).

Outputs:
  hartford-skyline.svg       two-tone (back buildings + front landmarks)
  hartford-skyline-mono.svg  single-colour silhouette

Requires: pip install shapely
"""
import math

from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

GY = 560                      # ground line
BACK_FILL = "#7d9cbb"         # steel blue
FRONT_FILL = "#1b2a3a"        # navy
BRAND = {"back": "#2f4254", "front": "#141d27", "dome": "#d9a05b"}
ACCENT = []                   # brand-mode extra layer (gilded dome)


# ── primitives ──────────────────────────────────────────────────────────────
def arc(cx, cy, rx, ry, a0, a1, step=1.5):
    """Points along an elliptical arc. SVG y-down: 180°=left, 270°=top, 360°=right."""
    n = max(6, int(math.radians(abs(a1 - a0)) * max(rx, ry) / step))
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def rect(x0, y0, x1, y1):
    return box(x0, y0, x1, y1)


def poly(*pts):
    return Polygon(pts)


def circle(cx, cy, r):
    return Point(cx, cy).buffer(r, quad_segs=16)


def dome(cx, base, rx, h):
    return Polygon(arc(cx, base, rx, h, 180, 360))


def arched(x0, x1, spring, bottom):
    """Round-headed opening."""
    r = (x1 - x0) / 2
    return Polygon([(x0, bottom)] + arc(x0 + r, spring, r, r, 180, 360) + [(x1, bottom)])


def pointed(x0, x1, spring, bottom):
    """Equilateral Gothic (pointed) arch opening."""
    w = x1 - x0
    return Polygon([(x0, bottom)] + arc(x1, spring, w, w, 180, 240)
                   + arc(x0, spring, w, w, 300, 360) + [(x1, bottom)])


def grid(x0, y0, x1, y1, w, h, px, py, kind="rect"):
    """Centre a grid of w×h openings at pitch (px, py) inside a region."""
    cols = int((x1 - x0 - w) // px) + 1
    rows = int((y1 - y0 - h) // py) + 1
    ox = x0 + ((x1 - x0) - ((cols - 1) * px + w)) / 2
    oy = y0 + ((y1 - y0) - ((rows - 1) * py + h)) / 2
    out = []
    for i in range(cols):
        for j in range(rows):
            X, Y = ox + i * px, oy + j * py
            if kind == "rect":
                out.append(rect(X, Y, X + w, Y + h))
            elif kind == "arch":
                out.append(arched(X, X + w, Y + w / 2, Y + h))
            elif kind == "pointed":
                out.append(pointed(X, X + w, Y + 0.866 * w, Y + h))
            elif kind == "circle":
                out.append(circle(X + w / 2, Y + h / 2, w / 2))
    return out


def crenel(x0, x1, y, h, mw, gap):
    """Battlement merlons sitting on line y, flush with both ends."""
    n = max(1, round((x1 - x0 - mw) / (mw + gap)))
    pitch = (x1 - x0 - mw) / n
    return [rect(x0 + i * pitch, y - h, x0 + i * pitch + mw, y) for i in range(n + 1)]


class Layer:
    def __init__(self):
        self.solids, self.holes = [], []

    def add(self, *geoms):
        for g in geoms:
            self.solids.extend(g if isinstance(g, list) else [g])

    def cut(self, *geoms):
        for g in geoms:
            self.holes.extend(g if isinstance(g, list) else [g])


def flag(layer, x, base, top, w=24, h=14):
    layer.add(rect(x - 1, top, x + 1, base), circle(x, top, 1.8))
    ts = [i / 12 for i in range(13)]
    wave = [2 * math.sin(2 * math.pi * t) * t for t in ts]
    upper = [(x + 1 + w * t, top + 2 + o) for t, o in zip(ts, wave)]
    lower = [(x + 1 + w * t, top + 2 + h + o) for t, o in zip(ts, wave)]
    layer.add(Polygon(upper + lower[::-1]))


# ── back layer (steel blue) ─────────────────────────────────────────────────
def back_buildings(B):
    # Left residential tower + slanted-roof neighbour
    B.add(rect(130, 206, 262, GY), rect(166, 192, 226, 208), rect(182, 182, 204, 194))
    B.cut(grid(138, 216, 254, 556, 9, 6, 15, 12))
    B.add(poly((250, GY), (250, 262), (362, 292), (362, GY)))

    # Low office block behind the bridge
    B.add(rect(424, 436, 556, GY))
    B.cut(grid(430, 446, 550, 556, 7, 10, 13, 18))
    flag(B, 440, 436, 400)

    # Travelers Tower
    B.add(rect(548, 410, 584, GY))                         # annex
    B.cut(grid(552, 420, 580, 548, 6, 8, 12, 15))
    B.add(rect(580, 262, 688, GY), rect(576, 258, 692, 266))   # shaft + cornice
    B.cut(grid(586, 278, 682, 548, 7, 9, 13, 15))
    B.add(rect(592, 200, 676, 262))                         # colonnaded top stage
    B.cut(grid(600, 214, 668, 254, 12, 40, 20, 100, "arch"))
    for px in (588, 670):                                   # corner piers + urns
        B.add(rect(px, 196, px + 10, 262), poly((px - 1, 196), (px + 5, 182), (px + 11, 196)))
    B.add(rect(590, 196, 678, 203))
    B.add(poly((600, 197), (622, 126), (646, 126), (668, 197)))   # pyramid roof
    B.cut(grid(620, 146, 648, 168, 5, 20, 10, 100, "arch"))       # dormers
    B.add(rect(618, 121, 650, 127), rect(623, 94, 645, 122))      # ledge + lantern
    B.cut(arched(630, 638, 104, 118))
    B.add(dome(634, 95, 13, 12), rect(632.8, 52, 635.2, 86), circle(634, 70, 2.6))

    # Art-deco stepped tower behind the Capitol
    B.add(rect(846, 236, 962, GY), rect(858, 196, 950, 240),
          rect(870, 160, 938, 200), rect(884, 130, 924, 164), rect(902.5, 84, 905.5, 132))
    B.cut(grid(852, 246, 956, 556, 5, 9, 11, 15), grid(864, 206, 944, 232, 5, 9, 11, 15),
          grid(876, 168, 932, 194, 5, 9, 11, 15), grid(890, 138, 918, 158, 4, 14, 8, 30))

    # Small block between Capitol and City Place
    B.add(rect(960, 318, 1034, GY))
    B.cut(grid(966, 328, 1028, 556, 6, 8, 12, 16))

    # City Place I — chamfered crown
    B.add(poly((1030, GY), (1030, 44), (1040, 44), (1040, 34), (1048, 34), (1048, 26),
               (1196, 26), (1196, 34), (1204, 34), (1204, 44), (1214, 44), (1214, GY)))
    B.cut(grid(1054, 46, 1190, 58, 5, 12, 10, 100), grid(1042, 74, 1202, 552, 3, 478, 12, 1000))

    # Gold Building — ribbon windows with mullions
    B.add(rect(1288, 178, 1446, GY), rect(1330, 164, 1390, 180))
    for y in range(192, 548, 12):
        for x in range(1296, 1438, 22):
            B.cut(rect(x, y, min(x + 19, 1438), y + 5))

    # Low block far right
    B.add(rect(1446, 400, 1530, GY))
    B.cut(grid(1452, 410, 1524, 556, 6, 9, 12, 16))


# ── front layer (navy) ──────────────────────────────────────────────────────
def memorial_arch(F):
    """Soldiers and Sailors Memorial Arch, Bushnell Park."""
    for x0, x1, top, tip in ((126, 176, 410, 314), (270, 320, 422, 338)):
        m = (x0 + x1) / 2
        F.add(rect(x0, top, x1, GY), rect(x0 - 5, top - 14, x1 + 5, top))
        F.add(poly((x0 - 3, top - 14), (m, tip), (x1 + 3, top - 14)))
        F.add(rect(m - 1, tip - 12, m + 1, tip + 2), circle(m, tip - 12, 2))
        F.cut(grid(x0 - 3, top - 9, x1 + 3, top - 4, 3, 5, 6, 100))   # corbel table
        F.cut(arched(m - 4, m + 4, top + 14, top + 34), arched(m - 4, m + 4, top + 62, top + 86))
    F.add(rect(176, 448, 270, GY), crenel(176, 270, 448, 8, 8, 6))
    F.cut(grid(184, 454, 262, 460, 5, 5, 10, 100, "circle"))          # frieze
    F.cut(arched(190, 256, 500, GY))


def bridge(F):
    x0, x1 = 318, 580
    F.add(rect(x0, 506, x1, GY), rect(x0, 495, x1, 498.5))
    for x in range(x0, x1 + 1, 14):
        F.add(rect(x, 495, x + 2.5, 506))
    for cx in (365.5, 449, 532.5):
        F.cut(Polygon(arc(cx, GY, 36, 36, 180, 360)))
    F.cut(circle(407.3, 516, 5), circle(490.8, 516, 5))


def capitol(F):
    """Connecticut State Capitol — symmetric about x=800."""
    F.add(rect(600, 440, 1000, GY), poly((598, 440), (608, 428), (992, 428), (1002, 440)))

    for x0 in (576, 972):                                     # end pavilions
        x1, m = x0 + 52, x0 + 26
        F.add(rect(x0, 418, x1, GY), rect(x0 - 3, 414, x1 + 3, 420))
        F.add(poly((x0 - 1, 414), (m, 374), (x1 + 1, 414)), rect(m - 1, 362, m + 1, 376))
        F.cut(circle(m, 429, 5))

    for g in (675, 925):                                      # gables w/ rose windows
        F.add(poly((g - 27, 432), (g, 400), (g + 27, 432)))
        for p in (g - 27, g + 27):
            F.add(poly((p - 3, 434), (p, 412), (p + 3, 434)))
        F.cut(circle(g, 419, 5))

    for cx in (722, 878):                                     # flanking spired towers
        F.add(rect(cx - 16, 410, cx + 16, GY), rect(cx - 19, 404, cx + 19, 410))
        F.add(poly((cx - 14, 404), (cx, 346), (cx + 14, 404)), rect(cx - 0.8, 334, cx + 0.8, 348))
        for s in (-1, 1):
            F.add(poly((cx + s * 19, 404), (cx + s * 16, 386), (cx + s * 13, 404)))
        F.cut(pointed(cx - 4, cx + 4, 425, 436))

    F.add(rect(744, 400, 856, GY), rect(740, 398, 860, 404))  # central pavilion
    for p in (744, 856):
        F.add(poly((p - 4, 402), (p, 376), (p + 4, 402)))
    F.cut(grid(750, 410, 850, 434, 8, 24, 14, 100, "pointed"))

    F.add(rect(764, 344, 836, 400))                           # tower base
    F.cut(arched(776, 790, 362, 394), arched(810, 824, 362, 394))
    for tx in (758, 832):
        F.add(rect(tx, 330, tx + 10, 400), poly((tx - 1, 330), (tx + 5, 312), (tx + 11, 330)))
    F.add(rect(756, 338, 844, 346))                           # gallery
    F.add(rect(770, 270, 830, 338))                           # drum
    F.cut(grid(774, 286, 826, 328, 7, 42, 14, 100, "arch"))
    F.add(rect(766, 262, 834, 271), dome(800, 263, 31, 44))   # cornice + gilded dome
    F.add(rect(791, 196, 809, 224))                           # lantern
    F.cut(arched(797, 803, 205, 218))
    F.add(dome(800, 197, 11, 9), rect(799.2, 166, 800.8, 190), circle(800, 176, 2.4))
    # brand mode paints the gilded dome in its own layer — it really is gold
    ACCENT.extend([dome(800, 263, 31, 44), rect(791, 196, 809, 224),
                   dome(800, 197, 11, 9), rect(799.2, 166, 800.8, 190),
                   circle(800, 176, 2.4)])

    rows = [(448, 468), (482, 506), (520, 548)]               # facade windows
    for x0, x1 in ((582, 622), (632, 700), (708, 736), (748, 778),
                   (822, 852), (864, 892), (900, 968), (978, 1018)):
        for y0, y1 in rows:
            F.cut(grid(x0, y0, x1, y1, 8, y1 - y0, 14, 100, "arch"))
    F.cut(grid(786, 448, 814, 468, 8, 20, 12, 100, "arch"), circle(800, 494, 9),
          arched(788, 812, 532, GY))                          # entrance


def right_side(F):
    # Mid-rise with flag
    F.add(rect(1024, 282, 1156, GY))
    F.cut(grid(1032, 292, 1148, 556, 6, 9, 12, 16))
    flag(F, 1040, 282, 246)

    # Stepped tower with arched crown
    F.add(rect(1156, 176, 1294, GY), rect(1172, 150, 1278, 178), rect(1192, 134, 1258, 152),
          rect(1212, 122, 1238, 136), rect(1224, 96, 1226, 124))
    F.cut(grid(1164, 188, 1286, 556, 7, 9, 13, 15), grid(1178, 156, 1272, 174, 7, 16, 13, 30, "arch"),
          grid(1198, 138, 1252, 150, 5, 10, 10, 30, "arch"))

    # Low connector
    F.add(rect(1290, 456, 1336, GY))
    F.cut(grid(1296, 466, 1330, 556, 6, 9, 12, 16))

    # Crenellated Gothic hall
    F.add(rect(1350, 470, 1466, GY), crenel(1350, 1466, 470, 8, 7, 7))
    for x0, x1, top in ((1330, 1368, 432), (1458, 1494, 444)):
        m = (x0 + x1) / 2
        F.add(rect(x0, top, x1, GY), rect(x0 - 2, top, x1 + 2, top + 6), crenel(x0 - 2, x1 + 2, top, 8, 6, 6))
        F.cut(pointed(m - 4, m + 4, top + 20, top + 38), pointed(m - 4, m + 4, top + 58, top + 78))
    F.add(rect(1396, 426, 1420, 470), crenel(1394, 1422, 426, 7, 5, 5))
    F.cut(circle(1408, 444, 4))
    F.cut(grid(1372, 490, 1398, 530, 9, 40, 16, 100, "pointed"),
          grid(1418, 490, 1450, 530, 9, 40, 16, 100, "pointed"),
          pointed(1402, 1414, 538, GY))

    # Small block far right
    F.add(rect(1494, 500, 1536, GY))
    F.cut(grid(1500, 508, 1530, 556, 6, 9, 12, 16))


def ground(F):
    F.add(rect(57, GY, 1543, GY + 34), circle(57, GY + 17, 17), circle(1543, GY + 17, 17))


# ── SVG output ──────────────────────────────────────────────────────────────
def fmt(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


def path_d(geom):
    polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    parts = []
    for p in polys:
        for ring in [p.exterior, *p.interiors]:
            pts = list(ring.coords)[:-1]
            parts.append("M" + " ".join(f"{fmt(x)},{fmt(y)}" for x, y in pts) + "Z")
    return "".join(parts)


def svg(layers, bounds, pad=20):
    x0, y0, x1, y1 = bounds
    vb = f"{fmt(x0 - pad)} {fmt(y0 - pad)} {fmt(x1 - x0 + 2 * pad)} {fmt(y1 - y0 + 2 * pad)}"
    body = "\n".join(f'  <path id="{lid}" fill="{fill}" fill-rule="evenodd" d="{path_d(g)}"/>'
                     for lid, fill, g in layers)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">\n'
            f"  <title>Hartford, Connecticut skyline</title>\n{body}\n</svg>\n")


def main():
    B, F = Layer(), Layer()
    back_buildings(B)
    memorial_arch(F)
    bridge(F)
    capitol(F)
    right_side(F)
    ground(F)

    front_solid = unary_union(F.solids)
    front = front_solid.difference(unary_union(F.holes)).simplify(0.05)
    back = (unary_union(B.solids).difference(unary_union(B.holes))
            .difference(front_solid).simplify(0.05))
    # One colour can't separate layers, so carve a thin halo around the
    # front landmarks to keep them legible against the towers behind.
    halo = front_solid.buffer(3, join_style="mitre")
    mono = unary_union([front, back.difference(halo)]).simplify(0.05)
    bounds = unary_union([front, back]).bounds

    import sys
    if "--brand" in sys.argv:
        acc = unary_union(ACCENT).simplify(0.05)
        with open("hartford-skyline-brand.svg", "w") as f:
            f.write(svg([("back-buildings", BRAND["back"], back),
                         ("front-landmarks", BRAND["front"], front),
                         ("gilded-dome", BRAND["dome"], acc)], bounds))
        print("brand svg written")

    with open("hartford-skyline.svg", "w") as f:
        f.write(svg([("back-buildings", BACK_FILL, back), ("front-landmarks", FRONT_FILL, front)], bounds))
    with open("hartford-skyline-mono.svg", "w") as f:
        f.write(svg([("skyline", FRONT_FILL, mono)], bounds))
    print("bounds", [round(b, 1) for b in bounds],
          "| holes:", sum(len(p.interiors) for p in getattr(mono, "geoms", [mono])))


if __name__ == "__main__":
    main()
