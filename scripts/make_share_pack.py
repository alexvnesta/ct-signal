"""One command, one share kit for a published card.

  <runtime-python> scripts/make_share_pack.py <card_id>

Ensures the static chart render (assets/share-<id>.png — the same file the
story page links) is current, then prints a paste-ready data-and-method
comment for venues like r/dataisbeautiful, where the best OC posts ship
their data and method as the top comment. Ours is generated verbatim from
the card's own provenance, so the comment cannot drift from the chart.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ctsignal import config, share  # noqa: E402


def main(card_id: str) -> int:
    cards = json.loads((config.ROOT / "output" /
                        "cards.json").read_text())["cards"]
    card = next((c for c in cards if c["id"].startswith(card_id)), None)
    if card is None:
        print(f"no card {card_id} in the published feed", file=sys.stderr)
        return 1
    png = share.export(card, config.ROOT / "assets")
    url = f"{config.SITE_URL}/story/{card['id']}/"
    cites = "\n".join(f"- {c}" for c in card.get("citations", [])) or "- see story page"
    png_line = (
        f"Chart file: {png.relative_to(ROOT)} (2x PNG, rendered server-side "
        "from the same spec the page draws)" if png else
        "Chart file: unavailable in this runtime (page chart is live)")
    print(f"""Title suggestion: {card['question']}

{png_line}

Data and method (every number fetched, none hand-edited):
{cites}
- Query as run: {card.get('query', 'see story provenance')}
- Pulled: {card['generated_at']}
- Story, provenance, and the news item that opened this question: {url}
- Static site: the pipeline's public git history is the audit trail.
""".rstrip())
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
