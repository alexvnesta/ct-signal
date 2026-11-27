"""Static share export: the page's chart, frozen, no browser involved.

Reddit and friends want a PNG, but the charts here are Vega-Lite rendered
by the same engine the page's CDN script uses — vl-convert embeds that
engine, so the download can never disagree with the picture on the page.

Export is opportunistic: no renderer (or a spec it cannot compile) yields
None and the story page simply omits the download line. A missing share
file degrades the page; it never breaks a cycle.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib

EXPORT_WIDTH = 680          # px; 2x scale below, so the file lands ~1360 wide
BG = "#0e141b"              # site background: PNGs must read on Reddit white
SHARE_INK = "#f3efe6"
SHARE_DIM = "#c9c3b6"
SHARE_GRID = "#2b333c"
SHARE_RULE = "#5a616a"


def _export_spec(spec: dict) -> dict:
    copy = json.loads(json.dumps(spec))
    copy["width"] = EXPORT_WIDTH
    copy["background"] = BG
    copy.pop("autosize", None)   # "container" is meaningless without a DOM
    # The page chart is configured for paper; the share card is a dark brand
    # canvas. Repaint its text and rules here or the title is ink on ink.
    cfg = copy.setdefault("config", {})
    axis = dict(cfg.get("axis") or {})
    axis.update(labelColor=SHARE_DIM, titleColor=SHARE_DIM,
                gridColor=SHARE_GRID, domainColor=SHARE_RULE,
                tickColor=SHARE_RULE)
    cfg["axis"] = axis
    legend = dict(cfg.get("legend") or {})
    legend.update(labelColor=SHARE_DIM, titleColor=SHARE_DIM)
    cfg["legend"] = legend
    title = dict(cfg.get("title") or {})
    title.update(color=SHARE_INK, subtitleColor=SHARE_DIM)
    cfg["title"] = title
    view = dict(cfg.get("view") or {})
    view["strokeWidth"] = 0
    cfg["view"] = view
    # Repaint dark paper-ink direct labels inside layered charts (e.g. top-N
    # bar-end labels) so they remain readable on the dark share canvas.
    for layer in copy.get("layer") or []:
        mark = layer.get("mark")
        mtype = mark.get("type") if isinstance(mark, dict) else mark
        if mtype == "text":
            col = (layer.get("encoding") or {}).get("color") or {}
            scale = col.get("scale") or {}
            rng = scale.get("range")
            if isinstance(rng, list):
                scale["range"] = [
                    SHARE_INK if c == "#1c2733" else
                    SHARE_DIM if c == "#4c5a68" else c
                    for c in rng
                ]
    return copy


def _paper_svg_spec(spec: dict) -> dict:
    """Static paper-palette spec for instant zero-JS first paint.
    Uses a fixed viewport width so vl-convert produces a clean viewBox SVG
    that scales fluidly before Vega-Embed hydrates interactivity."""
    copy = json.loads(json.dumps(spec))
    copy["width"] = 580
    copy["background"] = "transparent"
    copy.pop("autosize", None)
    return copy


def export_svg(card: dict, assets_dir: pathlib.Path) -> pathlib.Path | None:
    """Write assets/chart-<id>.svg (paper palette) for zero-flash SSR chart
    paint on mobile and desktop before Vega-Embed loads."""
    spec = card.get("chart")
    if not spec:
        return None
    payload = json.dumps(_paper_svg_spec(spec), sort_keys=True)
    digest = hashlib.sha1(payload.encode()).hexdigest()
    out = assets_dir / f"chart-{card['id']}.svg"
    stamp = assets_dir / f"chart-{card['id']}.svg.ver"
    if out.exists() and stamp.exists():
        try:
            if stamp.read_text().strip() == digest:
                return out
        except OSError:
            pass
    try:
        import vl_convert
        svg = vl_convert.vegalite_to_svg(payload)
        if not svg:
            return None
    except Exception:
        return None
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(svg, encoding="utf-8")
    os.replace(tmp, out)
    stamp.write_text(digest)
    return out


def export(card: dict, assets_dir: pathlib.Path) -> pathlib.Path | None:
    """Write assets/share-<id>.png when the chart spec changed (or the file
    is missing); return the path, or None if nothing could be rendered."""
    spec = card.get("chart")
    if not spec:
        return None
    payload = json.dumps(_export_spec(spec), sort_keys=True)
    digest = hashlib.sha1(payload.encode()).hexdigest()
    out = assets_dir / f"share-{card['id']}.png"
    stamp = assets_dir / f"share-{card['id']}.png.ver"
    if out.exists() and stamp.exists():
        try:
            if stamp.read_text().strip() == digest:
                return out
        except OSError:
            pass
    try:
        import vl_convert
        png = None
        # vl-convert 1.x takes `scale`, 2.x renamed it to `scale_factor`;
        # support both so one requirement line covers py3.13 and py3.14
        for kw in ("scale", "scale_factor"):
            try:
                png = vl_convert.vegalite_to_png(payload, **{kw: 2})
                break
            except TypeError:
                continue
        if not png:
            return None
    except Exception:
        return None
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_bytes(png)
    os.replace(tmp, out)
    stamp.write_text(digest)
    return out
