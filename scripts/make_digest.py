"""Weekly email digest, rendered from the same artefacts the site serves.

    python3 scripts/make_digest.py        # -> output/digest/<ISO-week>.html

Email-friendly by construction: inline styles, no external assets, links
absolute. Sending (Buttondown or anything else) is a separate concern — this
just freezes an issue nobody can accidentally edit later.
"""
import datetime as dt
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
try:
    from _brand import SITE  # noqa: E402  (shared brand recipe)
except ModuleNotFoundError:      # html-only runs (CI) need no Pillow
    SITE = "https://ctsignal.org"
E = html.escape


def main() -> None:
    feed = json.loads((ROOT / "output" / "cards.json").read_text())
    board = json.loads((ROOT / "board.json").read_text())
    cards = feed["cards"]
    if not cards:
        sys.exit("feed has no cards; nothing to digest")

    # Keep Connecticut-specific stories ahead of US macro context, and lead
    # with high-salience statewide/municipal findings rather than small-town
    # outliers or daily weather wobbles.
    _DIGEST_PRIORITY = {
        "housing_permits": 0, "mill_rates": 1, "home_sales_price": 2,
        "unemployment": 3, "school_spending_per_pupil": 4,
        "grand_list_growth": 5, "northeast_electricity": 6,
    }

    def _rank_key(c):
        src = str((c.get("headline") or {}).get("source", "")).lower()
        is_demo = "fixture" in src
        is_ct = (c.get("stream") in ("local", "stackup")
                 or c.get("indicator") in ("weather_anomaly", "ct_unemployment", "northeast_electricity"))
        prio = _DIGEST_PRIORITY.get(str(c.get("indicator") or ""), 20)
        return (1 if is_demo else 0, 0 if is_ct else 1, prio)

    cards = sorted(cards, key=_rank_key)
    week = dt.date.fromisoformat(
        max(c["generated_at"] for c in cards)[:10]).isocalendar()
    issue = f"{week.year}-W{week.week:02d}"
    lead_card = cards[0]
    if lead_card.get("indicator") == "housing_permits" and lead_card.get("towns"):
        top = lead_card["towns"][0]
        av = lead_card.get("answer_values") or {}
        total = int(av.get("state") or 0)
        if total > 0:
            lead = (f"{top['town']} permitted {top['value'] / total * 100:.1f}% of "
                    f"Connecticut's new housing in {av.get('date', '2025')}")
        else:
            lead = lead_card["answer_text"].split(" — ")[0].split(". ")[0]
    else:
        lead = lead_card["answer_text"].split(" — ")[0].split(". ")[0]
    # A dated window belongs in the body, not the subject line. Strip the
    # cadence clause when it is the only thing between a result and a reader.
    lead = re.sub(r"\s+over the \d+ days ending \d{4}-\d{2}-\d{2}", "",
                  lead).strip()
    subject = f"CT Signal: {lead}"

    def td(inner, weight="400", color="#e9eef4", size="15px"):
        return (f'<td style="padding:6px 10px;border-bottom:1px solid #24303e;'
                f'font:{weight} {size}/1.4 -apple-system,Segoe UI,Roboto,sans-serif;'
                f'color:{color}">{inner}</td>')

    rows = "".join(
        "<tr>"
        + td(E(t["title"]), "600")
        + td(E(t["value"]), "700", "#8fd6a9")
        + td(f'{E(t["rank_label"])} of {t["n"]} peers · data {E(t["date"])}',
             "400", "#7d91a5", "13px")
        + "</tr>"
        for t in board["tiles"])

    def demo_tag(c):
        src = str((c.get("headline") or {}).get("source", "")).lower()
        return ('' if "fixture" not in src else
                ' <span style="font:700 11px/1 ui-monospace,monospace;'
                'color:#c9a45c;border:1px solid #c9a45c;border-radius:3px;'
                'padding:1px 4px;vertical-align:2px">DEMO TRIGGER</span>')
    stories = "".join(
        f'<h2 style="font:700 17px/1.4 Georgia,serif;color:#e9eef4;margin:20px 0 4px">'
        f'<a href="{SITE}/story/{c["id"]}" style="color:#7fb4ff;text-decoration:none">'
        f'{E(c["question"])}</a>{demo_tag(c)}</h2>'
        f'<p style="font:15px/1.6 -apple-system,Segoe UI,Roboto,sans-serif;'
        f'color:#93a7b9;margin:0 0 2px">{E(c["answer_text"])}</p>'
        f'<p style="font:13px/1.4 -apple-system,Segoe UI,Roboto,sans-serif;'
        f'color:#7d91a5;margin:0"><a href="{SITE}/story/{c["id"]}" '
        f'style="color:#f2a65a;text-decoration:none">the chart and the query →</a></p>'
        for c in cards[:4])

    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>CT Signal digest {issue}</title></head>
<body style="margin:0;background:#0a0f14;padding:24px 12px">
<div style="max-width:560px;margin:0 auto;background:#0e141b;border:1px solid #24394e;
border-radius:12px;padding:24px">
<img src="{SITE}/assets/digest-header.png" width="512" alt="CT Signal"
style="width:100%;border-radius:8px;display:block;margin:0 0 16px">
<p style="font:700 12px/1 -apple-system,Segoe UI,Roboto,sans-serif;letter-spacing:.14em;
text-transform:uppercase;color:#f2a65a;margin:0">CT ⚡ SIGNAL · weekly board digest</p>
<p style="font:13px/1.4 -apple-system,Segoe UI,Roboto,sans-serif;color:#7d91a5;margin:6px 0 0">
Issue {issue} · <a href="{SITE}/week/{issue}" style="color:#7fb4ff;text-decoration:none">Read on the web →</a> · <a href="{SITE}/compare" style="color:#7fb4ff;text-decoration:none">Compare CT towns →</a></p>
<h1 style="font:700 21px/1.3 Georgia,serif;color:#e9eef4;margin:14px 0 10px">
{E(subject)}</h1>
<table role="presentation" width="100%" cellspacing="0" style="border-collapse:collapse;
background:#151d27;border-radius:8px">{rows}</table>
{stories}
<hr style="border:0;border-top:1px solid #24394e;margin:22px 0 12px">
<p style="font:12px/1.6 -apple-system,Segoe UI,Roboto,sans-serif;color:#7d91a5;margin:0">
CT Signal · <a href="{SITE}" style="color:#7fb4ff;text-decoration:none">{SITE}</a>
· <a href="{SITE}/week" style="color:#7fb4ff;text-decoration:none">Weekly archive</a>
· <a href="{SITE}/partner" style="color:#7fb4ff;text-decoration:none">Underwrite this digest</a>
· RSS: <a href="{SITE}/feed.xml" style="color:#7fb4ff;text-decoration:none">feed.xml</a><br>
Every dataset cited, with the literal query, on each story page. Corrections are public.<br>
You get this because you subscribed to the board digest — no trackers in this email.</p>
</div></body></html>
"""
    out_dir = ROOT / "output" / "digest"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{issue}.html"
    path.write_text(doc)
    meta = {
        "issue": issue,
        "subject": subject,
        "generated_at": max(c["generated_at"] for c in cards),
        "tiles": [
            {"title": t["title"], "value": t["value"],
             "rank_label": t.get("rank_label", ""), "n": t["n"], "date": t["date"]}
            for t in board.get("tiles", [])
        ],
        "stories": [
            {"id": c["id"], "topic": c.get("topic", ""), "stream": c.get("stream", ""),
             "question": c["question"], "answer_text": c["answer_text"],
             "date": str((c.get("answer_values") or {}).get("date") or "")}
            for c in cards[:6]
        ],
    }
    (out_dir / f"{issue}.json").write_text(json.dumps(meta, indent=2))
    # sidecars the send workflow reads: subject line and the newest-issue pointer
    (out_dir / "subject.txt").write_text(subject)
    (out_dir / "latest.txt").write_text(f"{issue}.html")
    print(f"digest issue {issue} -> {path.relative_to(ROOT)} ({len(doc)} bytes)")


if __name__ == "__main__":
    main()
