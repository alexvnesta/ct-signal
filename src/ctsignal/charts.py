from __future__ import annotations

from typing import Any, cast

import altair as alt

alt.data_transformers.disable_max_rows()
alt.data_transformers.consolidate_datasets = False

_HIGHLIGHT_COLOR = "#c0392b"
_MUTED_COLOR = "#9aa5b1"


def _pin_schema(spec: dict) -> dict:
    major = str(spec.get("$schema", "")).split("/v")[-1].split(".")[0] or "5"
    spec["$schema"] = f"https://vega.github.io/schema/vega-lite/v{major}.json"
    return spec


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
    return _pin_schema(cast(dict, chart.to_dict(validate=False)))
