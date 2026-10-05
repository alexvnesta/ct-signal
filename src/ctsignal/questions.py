from __future__ import annotations

import datetime as dt
import json
import re
import time

import requests
import yaml

from . import config


def load_catalog() -> dict:
    return yaml.safe_load(config.CATALOG_PATH.read_text())


def load_seeds(today: dt.date | None = None) -> list[dict]:
    today = today or dt.date.today()
    data = yaml.safe_load(config.SEEDS_PATH.read_text())
    out = []
    for seed in data.get("seeds", []):
        seed_date = dt.date.fromisoformat(str(seed["date"]))
        if abs((seed_date - today).days) <= int(seed.get("days_window", 14)):
            out.append(seed)
    return out


def _keyword_hits(title: str, keywords: list[str]) -> list[str]:
    lowered = title.lower()
    return [
        kw for kw in keywords
        if re.search(rf"\b{re.escape(kw)}\b", lowered)
    ]


def _answerable(item: dict) -> bool:
    """Only indicators with a question and an answer template may be asked.
    A catalog entry can otherwise be 'row-verified' as a dataset and still
    have no answerer wired, which turns every matching headline into a skip
    line in the log — a half-built card that keeps promising itself."""
    return bool(item.get("question") and item.get("answer"))


def propose_from_catalog(
    headline: dict, catalog: dict, stream: str
) -> list[dict]:
    pool = catalog.get("stackup" if stream == "stackup" else "local", [])
    # national-series context cards answer national headlines too: one
    # jobs-report day may open several honest questions at once
    extra = catalog.get("national", []) if stream == "stackup" else []
    proposals = []
    for pstream, items in ((stream, pool), ("national", extra)):
        for item in items:
            if not _answerable(item):
                continue
            hits = _keyword_hits(headline["title"], item.get("keywords", []))
            if not hits:
                continue
            proposals.append(
                {
                    "indicator_id": item["id"],
                    "stream": pstream,
                    "headline": headline,
                    "matched_keywords": hits,
                }
            )
    return proposals


def propose(headlines: list[dict], catalog: dict) -> list[dict]:
    proposals = []
    for headline in headlines:
        stream = "local" if headline["stream"] == "ct" else "stackup"
        proposals.extend(propose_from_catalog(headline, catalog, stream))
    for seed in load_seeds():
        proposals.append(
            {
                "indicator_id": seed.get("indicator"),
                "stream": seed["stream"],
                "headline": {
                    "id": f"seed-{seed['date']}",
                    "title": f"[civic calendar] {seed['reason']}",
                    "url": "",
                    "source": "civic calendar",
                    "published": seed["date"],
                    "published_sort": 0,
                },
                "question_override": seed.get("question"),
                "matched_keywords": ["calendar"],
            }
        )
    return proposals


def _catalog_brief(catalog: dict) -> list[dict]:
    items = []
    for section in ("stackup", "local", "national"):
        for item in catalog.get(section, []):
            if not _answerable(item):
                continue
            items.append({
                "id": item["id"],
                "title": item.get("title") or item.get("question", item["id"]),
                "topic": item["topic"],
            })
    return items


def validate_proposals(proposals: list[dict], catalog: dict) -> list[dict]:
    known = {i["id"] for s in ("stackup", "local", "national")
             for i in catalog.get(s, []) if _answerable(i)}
    return [p for p in proposals if p.get("indicator_id") in known]


def _llm_json(prompt: str) -> list[dict]:
    errors = []
    for model in config.GEMINI_MODELS:
        body = None
        for _ in range(2):
            try:
                resp = requests.post(
                    config.gemini_endpoint(model),
                    headers={"x-goog-api-key": config.GEMINI_API_KEY,
                             "Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0,
                                             "maxOutputTokens": 512,
                                             "responseMimeType": "application/json"},
                    },
                    timeout=45,
                )
            except requests.RequestException as exc:
                errors.append(f"{model}: {exc}")
                continue
            if resp.status_code in (429, 500, 502, 503):
                errors.append(f"{model}: HTTP {resp.status_code}")
                time.sleep(4)
                continue
            resp.raise_for_status()
            body = resp.json()
            break
        if body is None:
            continue
        parts = body.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()
        start, end = text.find("["), text.rfind("]")
        if start == -1 or end <= start:
            errors.append(f"{model}: empty response")
            continue
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError as exc:
            errors.append(f"{model}: bad json ({exc})")
    raise RuntimeError("Gemini unavailable: " + "; ".join(errors[:4]))


def propose_with_llm(headlines: list[dict], catalog: dict) -> list[dict]:
    if not config.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")
    brief = _catalog_brief(catalog)
    payload_headlines = [
        {"hid": h["id"], "title": h["title"]} for h in headlines[:24]
    ]
    prompt = (
        "You generate questions for CT Signal: a system that answers "
        "news-triggered questions about Connecticut from official data. "
        "The CATALOG is a closed set of answerable indicators. "
        "Return ONLY a JSON array like [{\"indicator_id\":\"...\",\"headline_id\":\"...\"}]. "
        "Include a pair only if the headline is genuinely about that "
        "indicator as a population-level trend (not one house, person, or "
        "case study); precision over recall; max 3 pairs per headline. "
        f"\nCATALOG: {json.dumps(brief)}\nHEADLINES: {json.dumps(payload_headlines)}"
    )
    pairs = _llm_json(prompt)
    stackup_ids = {i["id"] for i in catalog.get("stackup", [])}
    local_ids = {i["id"] for i in catalog.get("local", [])}
    national_ids = {i["id"] for i in catalog.get("national", [])}
    by_hid = {h["id"]: h for h in headlines}
    proposals = []
    for pair in pairs:
        iid, hid = pair.get("indicator_id"), pair.get("headline_id")
        headline = by_hid.get(hid)
        if not headline:
            continue
        if iid in stackup_ids:
            stream = "stackup"
        elif iid in local_ids:
            stream = "local"
        elif iid in national_ids:
            stream = "national"
        else:
            continue
        proposals.append({
            "indicator_id": iid,
            "stream": stream,
            "headline": headline,
            "matched_keywords": ["llm"],
        })
    return validate_proposals(proposals, catalog)
