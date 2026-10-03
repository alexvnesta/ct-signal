"""Tiny shared helpers: atomic writes and honest timestamps."""
from __future__ import annotations

import datetime as dt
import json
import os


def atomic_write_text(path, text: str) -> None:
    """Write via tmp+rename: a kill mid-write can never truncate a committed
    artifact (a half-written pipeline state once meant an empty board)."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def write_json(path, obj) -> None:
    atomic_write_text(path, json.dumps(obj, indent=2, sort_keys=True,
                                       default=str))


def parse_ts(ts: str) -> dt.datetime:
    """Parse ISO timestamps; naive values (older card vintages) mean UTC."""
    d = dt.datetime.fromisoformat(ts)
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


# ------------------------------------------------------------------- time ---
# Every reader of a Connecticut paper is in one state: show them that clock,
# never a raw UTC stamp with an assumed zone.
try:
    from zoneinfo import ZoneInfo
    _ET = ZoneInfo("America/New_York")
except Exception:                     # exotic host with no tzdata: say UTC
    _ET = dt.timezone.utc


def et(ts: str | dt.datetime) -> dt.datetime:
    """Any card timestamp rendered in the newsroom's own timezone (ET)."""
    d = ts if isinstance(ts, dt.datetime) else parse_ts(ts)
    return d.astimezone(_ET)


def clock(d_et: dt.datetime) -> str:
    """Wall clock with an honest zone label: '2:29 PM EDT'."""
    return f"{d_et:%-I:%M %p} {d_et.tzname() or 'UTC'}"
