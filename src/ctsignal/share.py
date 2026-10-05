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


def _export_spec(spec: dict) -> dict:
    copy = json.loads(json.dumps(spec))
    copy["width"] = EXPORT_WIDTH
    copy["background"] = BG
    copy.pop("autosize", None)   # "container" is meaningless without a DOM
    return copy


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
