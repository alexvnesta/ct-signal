from __future__ import annotations

from typing import Any, cast

import altair as alt

alt.data_transformers.disable_max_rows()
alt.data_transformers.consolidate_datasets = False

_HIGHLIGHT_COLOR = "#f2a65a"
_MUTED_COLOR = "#9aa5b1"


def _pin_schema(spec: dict) -> dict:
    spec["$schema"] = "https://vega.github.io/schema/vega-lite/v5.json"
    spec["background"] = "transparent"
    return spec


def _dark(chart):
    return (
        chart
        .configure_axis(labelColor="#9fb0bf", titleColor="#9fb0bf",
                        gridColor="#26313d", domainColor="#26313d",
                        tickColor="#26313d")
        .configure_legend(labelColor="#9fb0bf", titleColor="#9fb0bf",
                          symbolStrokeWidth=0)
        .configure_title(color="#eef2f5", subtitleColor="#9fb0bf")
        .configure_view(strokeWidth=0)
    )


def _highlight_color() -> dict:
    return {
        "field": "highlight",
        "type": "nominal",
        "legend": None,
        "scale": {"domain": [True, False], "range": [_HIGHLIGHT_COLOR, _MUTED_COLOR]},
    }


def rank_strip(rows: list[dict], *, title: str, unit: str = "") -> dict:
    order = [r["state"] for r in sorted(rows, key=lambda r: -r["rank"])]
    chart = (
        alt.Chart(alt.Data(values=rows))
        .mark_bar(tooltip=False)
        .encode(
            x=alt.X("value:Q").title(f"{title}{f' ({unit})' if unit else ''}"),
            y=alt.Y("state:N").sort(order).title(None),
            color=cast(Any, _highlight_color()),
            tooltip=[
                alt.Tooltip("state:N").title("State"),
                alt.Tooltip("value:Q").title(title),
                alt.Tooltip("rank:Q").title("Rank"),
            ],
        )
        .properties(width=420, height=max(140, 14 * len(rows)),
                    title=alt.TitleParams(text=title, subtitle="Connecticut highlighted"))
    )
    chart = _dark(chart)
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
                alt.Tooltip("state:N").title("State"),
                alt.Tooltip("rank:Q").title("Rank"),
            ],
        )
        .properties(width="container", height=46,
                    title=alt.TitleParams(text=title, fontSize=11, color="#69788a"))
    )
    chart = _dark(chart)
    return _pin_schema(cast(dict, chart.to_dict(validate=False)))


def state_map(rows: list[dict], *, title: str, unit: str = "") -> dict:
    topo = alt.topo_feature(url="us.json", feature="states")
    joined = alt.Chart(topo).transform_lookup(
        lookup="properties.name",
        from_=alt.LookupData(data=alt.Data(values=rows), key="state",
                             fields=["value", "rank"]),
    )
    base = (
        joined.mark_geoshape(stroke="#22303c", strokeWidth=0.4)
        .encode(
            color=alt.Color("value:Q")
            .title(f"{title}{f' ({unit})' if unit else ''}")
            .legend(alt.Legend(orient="bottom", direction="horizontal",
                               gradientLength=180)),
            tooltip=[
                alt.Tooltip("properties.name:N").title("State"),
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
    chart = _dark(chart)
    return _pin_schema(cast(dict, chart.to_dict(validate=False)))


def trend(rows: list[dict], *, title: str, unit: str = "") -> dict:
    series = alt.Color("series:N").legend(alt.Legend(title=None)).scale(
        domain=["Connecticut", "United States"], range=[_HIGHLIGHT_COLOR, _MUTED_COLOR]
    )
    chart = (
        alt.Chart(alt.Data(values=rows))
        .mark_line(point=True)
        .encode(
            x=alt.X("date:O").title("Date"),
            y=alt.Y("value:Q").title(f"{title}{f' ({unit})' if unit else ''}"),
            color=series,
            tooltip=[
                alt.Tooltip("series:N"),
                alt.Tooltip("date:O"),
                alt.Tooltip("value:Q"),
            ],
        )
        .properties(width=420, height=200, title=alt.TitleParams(text=title))
    )
    chart = _dark(chart)
    return _pin_schema(cast(dict, chart.to_dict(validate=False)))
