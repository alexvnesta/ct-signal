"""Build assets/ct-towns.json: the town-desk choropleth geometry.

Source of record: US Census cartographic boundary file, 2024 county
subdivisions for Connecticut at 1:500,000 (the generalized shape the
Census publishes for small-scale maps — the same vintage family the town
numbers come from). Boundaries are baked at build time; the page ships
plain SVG, no tiles, no scripts fetching basemaps, no cookies.

Run with the runtime python (stdlib only):
    python scripts/make_towns_map.py [--zip /path/to/cousub.zip]
"""
from __future__ import annotations

import json
import math
import pathlib
import struct
import sys
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
URL = ("https://www2.census.gov/geo/tiger/GENZ2024/shp/"
       "cb_2024_09_cousub_500k.zip")
OUT = ROOT / "assets" / "ct-towns.json"

LON0, LAT0 = -72.7, 41.6          # Connecticut's middle, roughly
KX = math.cos(math.radians(LAT0))  # conformal-ish x squeeze
SCALE = 900.0  # degrees to viewBox units (CT spans ~1.6 x 1.1 deg)


def _dbf_names(blob: bytes) -> list[str]:
    """The NAME column, record order == shapefile record order."""
    # field count comes from the header LENGTH (bytes 8-9): the descriptors
    # run until the 0x0D terminator, no further
    nf = (struct.unpack("<H", blob[8:10])[0] - 33) // 32
    fields = []
    for i in range(nf):
        f = blob[32 + i * 32: 64 + i * 32]
        fields.append((f[:11].split(b"\0")[0].decode(), f[16]))
    name_idx = next(i for i, (n, _) in enumerate(fields) if n == "NAME")
    wlen = struct.unpack("<H", blob[10:12])[0]
    nrec = struct.unpack("<L", blob[4:8])[0]
    off = struct.unpack("<H", blob[8:10])[0]   # header length, 16-bit
    out = []
    for r in range(nrec):
        rec = blob[off + r * wlen: off + (r + 1) * wlen]
        pos, vals = 1, []
        for _, ln in fields:
            vals.append(rec[pos:pos + ln])
            pos += ln
        out.append(vals[name_idx].decode("latin-1").strip())
    return out


def _polys(blob: bytes) -> list[list[tuple[list[tuple], bool]]]:
    """Per record: list of (ring, is_hole). Shape type 5, parts by
    orientation: clockwise rings are holes in shapefiles."""
    out = []
    pos = 100
    while pos < len(blob):
        num, clen = struct.unpack(">2i", blob[pos:pos + 8])
        pos += 8
        if clen == 0:                      # null shape
            out.append([])
            continue
        body = blob[pos:pos + clen * 2]
        pos += clen * 2
        stype = struct.unpack("<i", body[:4])[0]
        if stype != 5:
            out.append([])
            continue
        nparts, npts = struct.unpack("<2i", body[36:44])
        parts = struct.unpack(f"<{nparts}i", body[44:44 + 4 * nparts])
        # each vertex is 16 bytes: X and Y, two doubles — not one
        pts = struct.unpack(f"<{2 * npts}d", body[44 + 4 * nparts:
                                                 44 + 4 * nparts + 16 * npts])
        verts = list(zip(pts[0::2], pts[1::2]))
        rings = []
        for i, start in enumerate(parts):
            end = parts[i + 1] if i + 1 < len(parts) else npts
            ring = verts[start:end]
            area = sum((x2 - x1) * (y2 + y1)
                       for (x1, y1), (x2, y2) in zip(ring, ring[1:]))
            rings.append((ring, area < 0))   # negative signed area = hole
        out.append(rings)
    return out


def _proj(x: float, y: float) -> tuple[float, float]:
    return ((x - LON0) * KX * SCALE, (LAT0 - y) * SCALE)


def _path(rings, ox: float, oy: float, rnd=1) -> str:
    d = []
    for ring, _ in rings:
        pts = [(px - ox, py - oy) for px, py in (_proj(*p) for p in ring)]
        d.append("M" + "L".join(f"{x:.{rnd}f},{y:.{rnd}f}"
                                for x, y in pts) + "Z")
    return "".join(d)


def _area_km2(rings) -> float:
    a = 0.0
    for ring, hole in rings:
        s = abs(sum((x2 - x1) * (y2 + y1)
                    for (x1, y1), (x2, y2) in zip(ring, ring[1:]))) / 2
        a += -s if hole else s            # degrees^2, rank only
    return a * (KX * 111.32) * 111.32


def _centroid(rings, ox: float, oy: float):
    ring = max(rings, key=lambda r: len(r[0]))[0]
    xs, ys = zip(*(_proj(*p) for p in ring))
    return (sum(xs) / len(xs) - ox), (sum(ys) / len(ys) - oy)


def main() -> None:
    zip_path = pathlib.Path("/tmp/cousub.zip")
    if "--zip" in sys.argv:
        zip_path = pathlib.Path(sys.argv[sys.argv.index("--zip") + 1])
    if not zip_path.exists():
        urllib.request.urlretrieve(URL, zip_path)
    with zipfile.ZipFile(zip_path) as z:
        stem = "cb_2024_09_cousub_500k"
        shp = z.read(f"{stem}.shp")
        dbf = z.read(f"{stem}.dbf")
    names, records = _dbf_names(dbf), _polys(shp)
    # normalize against the TRUE bbox of every vertex, not centroids:
    # town shapes start negative in x (west of the origin line) otherwise
    kept = []
    for name, rings in zip(names, records):
        rings = [r for r in rings if len(r[0]) > 3]
        if not rings or _area_km2(rings) < 0.05:
            continue
        label = name.split(",")[0]
        label = (label.replace(" town", "").replace(" city", "")
                 .replace("village", "").strip())
        kept.append((label, rings))
    pts = [pt for _, rr in kept for ring, _ in rr for pt in
           (_proj(*p) for p in ring)]
    ox, oy = min(x for x, _ in pts), min(y for _, y in pts)
    mx = max(x for x, _ in pts)
    my = max(y for _, y in pts)
    towns = []
    for label, rings in kept:
        cx, cy = _centroid(rings, ox, oy)
        towns.append({"name": label, "d": _path(rings, ox, oy),
                      "cx": round(cx, 1), "cy": round(cy, 1)})
    w, h = mx - ox + 12, my - oy + 12
    towns.sort(key=lambda t: t["name"])
    OUT.write_text(json.dumps({
        "v": 1,
        "source": ("US Census Bureau cartographic boundaries, 2024, "
                   "county subdivisions of Connecticut (1:500,000)"),
        "width": round(w, 1), "height": round(h, 1), "towns": towns}))
    print(f"wrote {OUT.name}: {len(towns)} polygons, "
          f"{OUT.stat().st_size // 1024} KiB")


if __name__ == "__main__":
    main()
