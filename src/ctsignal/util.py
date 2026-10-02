"""Tiny shared helpers: atomic writes and honest timestamps."""
from __future__ import annotations

import datetime as dt
import json
import os


def atomic_write_text(path, text: str) -> None:
    """Write via tmp+rename: a kill mid-write can never truncate a committed
    artifact (a half-written output/feed.json once meant an empty board)."""
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
