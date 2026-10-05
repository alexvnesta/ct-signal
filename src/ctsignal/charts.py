from __future__ import annotations

from typing import Any, cast

import altair as alt

alt.data_transformers.disable_max_rows()
alt.data_transformers.consolidate_datasets = False

def _tick_fmt(unit: str) -> str:
    return {"USD": "$,.0f", "percent": ".1f", "per 100k": ",.0f"}.get(unit, ",.0f")


_HIGHLIGHT_COLOR = "#d9772b"
_MUTED_COLOR = "#b9b3a6"


def _pin_schema(spec: dict) -> dict:
    spec["$schema"] = "https://vega.github.io/schema/vega-lite/v6.json"
    spec["background"] = "transparent"
    return spec


def _paper(chart):
    """Paper palette: ink text, taupe rules, one amber highlight."""
    return (
        chart
        .configure_axis(labelColor="#4c5a68", titleColor="#4c5a68",
                        gridColor="#e4dfd3", domainColor="#b8b2a6",
                        tickColor="#b8b2a6")
        .configure_legend(labelColor="#4c5a68", titleColor="#4c5a68",
                          symbolStrokeWidth=0)
        .configure_title(color="#1c2733", subtitleColor="#66717e")
        .configure_view(strokeWidth=0)
    )


def _highlight_color() -> dict:
    return {
        "field": "highlight",
        "type": "nominal",
        "legend": None,
        "scale": {"domain": [True, False], "range": [_HIGHLIGHT_COLOR, _MUTED_COLOR]},
    }


def rank_strip(rows: list[dict], *, title: str, unit: str = "",
             peer_word: str = "Peer") -> dict:
    order = [r["state"] for r in sorted(rows, key=lambda r: -r["rank"])]
    hl = next((r["state"] for r in rows if r.get("highlight")), None)
    sub = (f'{hl} highlighted' if hl else
           'orange marks the peer the story is about')
    axis = (f'{title} ({unit})' if unit and unit not in title
            else f'{title}{f" ({unit})" if unit else ""}')
    chart = (
        alt.Chart(alt.Data(values=rows))
        .mark_bar(tooltip=False)
        .encode(
            x=alt.X("value:Q").title(axis)
                .axis(alt.Axis(format=_tick_fmt(unit))),
            y=alt.Y("state:N").sort(order).title(None),
            color=cast(Any, _highlight_color()),
            tooltip=[
                alt.Tooltip("state:N").title(peer_word),
                alt.Tooltip("value:Q").title(title),
                alt.Tooltip("rank:Q").title("Rank"),
            ],
        )
        .properties(width="container", height=max(140, 14 * len(rows)),
                    title=alt.TitleParams(text=title, subtitle=sub))
    )
    chart = _paper(chart)
    return _pin_schema(cast(dict, chart.to_dict(validate=False)))


def dot_strip(rows: list[dict], *, title: str = "") -> dict:
    strip = [{**r, "y": 0} for r in rows]
    order = list(range(1, len(strip) + 1))
    chart = (
        alt.Chart(alt.Data(values=strip))
        .mark_circle(size=42)
        .encode(
            x=alt.X("rank:O").sort(order).axis(alt.Axis(domain=False, ticks=False,
                labels=False, grid=False)).title(None),
            y=alt.Y("y:Q").axis(alt.Axis(domain=False, ticks=False, labels=False,
                grid=False)).title(None).scale(domain=[-0.5, 0.5]),
            color=cast(Any, _highlight_color()),
            tooltip=[
                alt.Tooltip("state:N").title("Peer"),
                alt.Tooltip("rank:Q").title("Rank"),
            ],
        )
        .properties(width="container", height=46,
                    title=alt.TitleParams(text=title, fontSize=11, color="#66717e"))
    )
    # No CT text tag here: layering breaks width:"container" resolution
    # (svg renders 0-wide). The orange dot + tooltip + board legend already
    # identify Connecticut; visual review over decoration.
    chart = _paper(chart)
    return _pin_schema(cast(dict, chart.to_dict(validate=False)))


def shape_strip(rows: list[dict]) -> dict:
    """The ranking's silhouette, small: every peer as a bar in rank order,
    true zero-based lengths, Connecticut in orange. The dot strip it replaced
    was 52 identical pills — a loading bar, not data. This is the same shape
    the story chart and the card thumbnail draw, so the board, the picture
    and the page agree at a glance."""
    ordered = sorted(rows, key=lambda r: r["rank"])
    chart = (
        alt.Chart(alt.Data(values=ordered))
        .mark_bar(tooltip=False)
        .encode(
            x=alt.X("rank:O").sort(list(range(1, len(ordered) + 1)))
                .axis(alt.Axis(domain=True, ticks=False, labels=False,
                               grid=False, tickCount=0)).title(None),
            y=alt.Y("value:Q")
                .axis(alt.Axis(domain=False, ticks=False, labels=False,
                               grid=False)).title(None),
            color=cast(Any, _highlight_color()),
            tooltip=[
                alt.Tooltip("state:N").title("Peer"),
                alt.Tooltip("value:Q").title("Value"),
                alt.Tooltip("rank:Q").title("Rank"),
            ],
        )
        .properties(width="container", height=68)
    )
    chart = _paper(chart)
    return _pin_schema(cast(dict, chart.to_dict(validate=False)))


def state_map(rows: list[dict], *, title: str, unit: str = "") -> dict:
    topo = alt.topo_feature(url="us.json", feature="states")
    joined = alt.Chart(topo).transform_lookup(
        lookup="properties.name",
        from_=alt.LookupData(data=alt.Data(values=rows), key="state",
                             fields=["value", "rank"]),
    )
    base = (
        joined.mark_geoshape(stroke="#b8b2a6", strokeWidth=0.4)
        .encode(
            color=alt.Color("value:Q")
            .title(f"{title}{f' ({unit})' if unit else ''}")
            .legend(alt.Legend(orient="bottom", direction="horizontal",
                               gradientLength=180)),
            tooltip=[
                alt.Tooltip("properties.name:N").title("Peer"),
                alt.Tooltip("value:Q").title(title),
                alt.Tooltip("rank:Q").title("Rank"),
            ],
        )
    )
    ct_outline = (
        alt.Chart(topo)
        .transform_filter(alt.FieldEqualPredicate(
            field="properties.name", equal="Connecticut"))
        .mark_geoshape(fill=None, stroke=_HIGHLIGHT_COLOR, strokeWidth=2)
    )
    chart = (
        alt.layer(base, ct_outline)
        .project(type="albersUsa")
        .properties(width=460, height=280, title=alt.TitleParams(text=title))
    )
    chart = _paper(chart)
    return _pin_schema(cast(dict, chart.to_dict(validate=False)))


def trend(rows: list[dict], *, title: str, unit: str = "",
          highlight_series: str = "Connecticut") -> dict:
    """Two-line CT-vs-US by default; national cards pass
    highlight_series="United States" so the one line on the chart is the
    one the answer is talking about — orange means 'the subject', not
    'Connecticut'."""
    names = sorted({r["series"] for r in rows})
    domain = ([highlight_series]
              + [n for n in names if n != highlight_series])
    range_ = ([_HIGHLIGHT_COLOR] + [_MUTED_COLOR] * (len(domain) - 1))
    series = alt.Color("series:N").legend(None).scale(
        domain=domain, range=range_
    )
    line = (
        alt.Chart(alt.Data(values=rows))
        .mark_line(point=True)
        .encode(
            x=alt.X("date:T").title(None).axis(
                alt.Axis(format="%Y", tickCount=6, grid=False,
                           domainColor="#c9c3b6")),
            y=alt.Y("value:Q").title(f"{title}{f' ({unit})' if unit else ''}")
                .axis(alt.Axis(format=_tick_fmt(unit))),
            color=series,
            tooltip=[
                alt.Tooltip("series:N"),
                alt.Tooltip("date:T").title("Month").format("%Y-%m"),
                alt.Tooltip("value:Q").format(".1f"),
            ],
        )
    )
    # FT-style direct labelling: name each series at its own endpoint —
    # no legend to decode, no colour-only signal.
    ends = []
    shorts = {"Connecticut": "CT", "United States": "US"}
    for name in domain:
        pts = [r for r in rows if r["series"] == name]
        if pts:
            e = max(pts, key=lambda r: str(r["date"]))
            ends.append({**e, "short": shorts.get(name, name[:2].upper())})
    labels = (
        alt.Chart(alt.Data(values=ends))
        .mark_text(align="left", dx=8, dy=-8, fontSize=12, fontWeight=700)
        .encode(x=alt.X("date:T"), y=alt.Y("value:Q"),
                text=alt.Text("short:N"),
                color=alt.Color("series:N", legend=None,
                                scale=alt.Scale(domain=domain, range=range_)))
    )
    chart = (line + labels).properties(
        width="container", height=200, title=alt.TitleParams(text=title),
        autosize=alt.AutoSizeParams(contains="padding"),
        padding=alt.Padding(right=64))
    chart = _paper(chart)
    return _pin_schema(cast(dict, chart.to_dict(validate=False)))
