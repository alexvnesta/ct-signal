"""Connecticut's own weather, from NOAA's ACIS service (keyless).

The card the ledger asked for: the wire reads weather constantly, and no
tracked dataset answered it. One state, two stations (Bradley Intl and
Danbury Municipal), each measured against its own 1991-2020 normals —
so 'warmer than normal' is arithmetic, never a mood. StnData quirks
honored: elems must be bare names or {"name":..., "normal":...} objects
(mixed lists 400), and normals come back as a separate call joined on
date."""
import json
import statistics
import urllib.request

import datetime as dt

from .. import config

BASE = "https://data.rcc-acis.org/StnData"
STATIONS = ("KBDL", "KDXR")
WINDOW_DAYS = 30


def _call(body: dict) -> dict:
    req = urllib.request.Request(
        BASE, data=json.dumps(body).encode(),
        headers={"User-Agent": "CTSignal/1.0; +https://ctsignal.org",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _window() -> tuple[str, str]:
    end = dt.date.today() - dt.timedelta(days=1)
    start = end - dt.timedelta(days=WINDOW_DAYS - 1)
    return start.isoformat(), end.isoformat()


def _num(x: str) -> float:
    return 0.0 if x in ("T", "S", "M", "A") else float(x)


def _anomaly(sid: str) -> dict | None:
    sdate, edate = _window()
    try:
        obs = _call({"sid": sid, "sdate": sdate, "edate": edate,
                     "elems": ["maxt", "mint", "pcpn"]})
        norm = _call({"sid": sid, "sdate": sdate, "edate": edate,
                      "elems": [{"name": "maxt", "normal": "1991-2020"},
                                {"name": "mint", "normal": "1991-2020"},
                                {"name": "pcpn", "normal": "1991-2020"}]})
    except Exception:
        return None
    nmap = {r[0]: r[1:] for r in norm.get("data", [])}
    tvals, tnorms, pvals, pnorms = [], [], [], []
    for row in obs.get("data", []):
        date, mx, mn, pr = row[0], row[1], row[2], row[3]
        n = nmap.get(date)
        if not n or "M" in (mx, mn) or "M" in n:
            continue
        tvals.append((int(mx) + int(mn)) / 2)
        tnorms.append((int(n[0]) + int(n[1])) / 2)
        pvals.append(_num(pr))
        pnorms.append(_num(n[2]))
    if len(tvals) < WINDOW_DAYS * 0.6:
        return None
    return {
        "station": sid,
        "days": len(tvals),
        "temp_anomaly": statistics.mean(tvals) - statistics.mean(tnorms),
        "precip": sum(pvals),
        "precip_normal": sum(pnorms),
    }


def _daily_rows() -> list[dict]:
    """One row per day per station: that day's mean temperature minus the
    same day's 1991-2020 normal. The trend chart then shows the window
    itself, not a two-point shorthand."""
    sdate, edate = _window()
    rows = []
    for sid in STATIONS:
        try:
            obs = _call({"sid": sid, "sdate": sdate, "edate": edate,
                         "elems": ["maxt", "mint"]})
            norm = _call({"sid": sid, "sdate": sdate, "edate": edate,
                          "elems": [{"name": "maxt", "normal": "1991-2020"},
                                    {"name": "mint", "normal": "1991-2020"}]})
        except Exception:
            continue
        nmap = {r[0]: r[1:] for r in norm.get("data", [])}
        for row in obs.get("data", []):
            date, mx, mn = row[0], row[1], row[2]
            n = nmap.get(date)
            if not n or "M" in (mx, mn) or "M" in n:
                continue
            rows.append({"date": date,
                         "series": {"KBDL": "Bradley Intl",
                                    "KDXR": "Danbury"}.get(sid, sid),
                         "value": round((int(mx) + int(mn)) / 2
                                        - (int(n[0]) + int(n[1])) / 2, 1)})
    return rows


def observations() -> dict | None:
    """Mean anomaly across stations that report; None when the service
    or the gauge is down — the cycle stays silent rather than inventing."""
    parts = [a for a in (_anomaly(s) for s in STATIONS) if a]
    if not parts:
        return None
    sdate, edate = _window()
    days = min(p["days"] for p in parts)
    return {
        "value": round(statistics.mean(p["temp_anomaly"] for p in parts), 1),
        "date": edate,
        "stations": [p["station"] for p in parts],
        "precip": round(sum(p["precip"] for p in parts) / len(parts), 2),
        "precip_normal": round(
            sum(p["precip_normal"] for p in parts) / len(parts), 2),
        "rows": _daily_rows(),
        "extreme": "",
        "citation": "https://data.rcc-acis.org/StnData",
        "query": (f"NOAA ACIS StnData sid={','.join(STATIONS)} "
                  f"elems=maxt,mint,pcpn normals=1991-2020; "
                  f"agency of record: NOAA Regional Climate Centers"),
        "cache": False,
    }
