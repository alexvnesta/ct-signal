"""Build one Bluesky createRecord payload for a freshly published card.

stdin: cards.json (HEAD version); env: ID (card id), BSKY_DID, OUT (path),
and optionally BSKY_BLOB_FILE (the uploadBlob response for the card's share
PNG). With a blob the post embeds the chart itself; without one it degrades
to the plain link card, so a failed upload never blocks the post.
Voice rule: the post states the answer, links the receipts, adds nothing.
Craft (per the text-post skill, aligned to house voice): the answer IS the
hook — a specific number about a known place earns the tap; the question
restates it and only wastes the fold, so the answer leads and the question
is left to the linked story.
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ctsignal import newsroom  # noqa: E402

card = next(c for c in json.load(sys.stdin)["cards"]
            if c["id"] == os.environ["ID"])
url = f"https://ctsignal.org/story/{card['id']}"
headline = newsroom._finding(card) or card["answer_text"]
text = (f"{headline}\n\n{url}\n"
        "Know where you live — sources on the page.")
if len(text) > 300:
    # Fit Bluesky's 300-grapheme cap without cutting the claim mid-sentence:
    # trim at the last sentence boundary, else the last word boundary.
    head = text[:297]
    cut = max(head.rfind(". "), head.rfind("! "), head.rfind("? "))
    if cut < 0:
        cut = head.rfind(" ")
    text = (text[:cut + 1].rstrip() if cut > 0 else head) + "..."

blob = None
blob_file = os.environ.get("BSKY_BLOB_FILE", "")
if blob_file:
    try:
        data = json.load(open(blob_file))
        candidate = data.get("blob") or data
        if isinstance(candidate, dict) and candidate.get("ref"):
            blob = candidate
    except Exception:
        blob = None

if blob:
    embed = {"$type": "app.bsky.embed.images", "images": [{
        "image": blob,
        "alt": f"{card['question']} — {headline}"[:280]}]}
else:
    embed = {"$type": "app.bsky.embed.external", "external": {
        "uri": url, "title": card["question"],
        "description": newsroom._display_prose(card["answer_text"])[:200]}}
rec = {
    "repo": os.environ["BSKY_DID"],
    "collection": "app.bsky.feed.post",
    "record": {
        "text": text,
        "createdAt": datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "embed": embed,
    },
}
json.dump(rec, open(os.environ.get("OUT", "/tmp/bsky_rec.json"), "w"))
