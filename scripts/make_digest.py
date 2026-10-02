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
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _brand import SITE  # noqa: E402  (shared brand recipe)
E = html.escape


def main() -> None:
    feed = json.loads((ROOT / "output" / "cards.json").read_text())
    board = json.loads((ROOT / "board.json").read_text())
    cards = feed["cards"]
    if not cards:
        sys.exit("feed has no cards; nothing to digest")

    week = dt.date.fromisoformat(
        max(c["generated_at"] for c in cards)[:10]).isocalendar()
    issue = f"{week.year}-W{week.week:02d}"
    lead = cards[0]["answer_text"].split(" — ")[0].split(". ")[0]
    subject = f"CT Signal: the board this week — {lead}"

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

    stories = "".join(
        f'<h2 style="font:700 17px/1.4 Georgia,serif;color:#e9eef4;margin:20px 0 4px">'
        f'<a href="{SITE}/story/{c["id"]}" style="color:#7fb4ff;text-decoration:none">'
        f'{E(c["question"])}</a></h2>'
        f'<p style="font:15px/1.6 -apple-system,Segoe UI,Roboto,sans-serif;'
        f'color:#93a7b9;margin:0 0 2px">{E(c["answer_text"])}</p>'
        f'<p style="font:13px/1.4 -apple-system,Segoe UI,Roboto,sans-serif;'
        f'color:#7d91a5;margin:0"><a href="{SITE}/story/{c["id"]}" '
        f'style="color:#f2a65a;text-decoration:none">the chart and the query →</a></p>'
        for c in cards[:3])

    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>CT Signal digest {issue}</title></head>
<body style="margin:0;background:#0a0f14;padding:24px 12px">
<div style="max-width:560px;margin:0 auto;background:#0e141b;border:1px solid #24394e;
border-radius:12px;padding:24px">
<p style="font:700 12px/1 -apple-system,Segoe UI,Roboto,sans-serif;letter-spacing:.14em;
text-transform:uppercase;color:#f2a65a;margin:0">CT ⚡ SIGNAL · weekly board digest</p>
<p style="font:13px/1.4 -apple-system,Segoe UI,Roboto,sans-serif;color:#7d91a5;margin:6px 0 0">
Issue {issue} · every number fetched from a named public dataset, never typed by hand</p>
<h1 style="font:700 21px/1.3 Georgia,serif;color:#e9eef4;margin:14px 0 10px">
{E(subject)}</h1>
<table role="presentation" width="100%" cellspacing="0" style="border-collapse:collapse;
background:#151d27;border-radius:8px">{rows}</table>
{stories}
<hr style="border:0;border-top:1px solid #24394e;margin:22px 0 12px">
<p style="font:12px/1.6 -apple-system,Segoe UI,Roboto,sans-serif;color:#7d91a5;margin:0">
CT Signal · <a href="{SITE}" style="color:#7fb4ff;text-decoration:none">{SITE}</a>
· RSS: <a href="{SITE}/feed.xml" style="color:#7fb4ff;text-decoration:none">feed.xml</a><br>
Every dataset cited, with the literal query, on each story page. Corrections are public.<br>
You get this because you subscribed to the board digest — no trackers in this email.</p>
</div></body></html>
"""
    out_dir = ROOT / "output" / "digest"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{issue}.html"
    path.write_text(doc)
    print(f"digest issue {issue} -> {path.relative_to(ROOT)} ({len(doc)} bytes)")


if __name__ == "__main__":
    main()
