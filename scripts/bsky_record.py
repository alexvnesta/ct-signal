"""Build one Bluesky createRecord payload for a freshly published card.

stdin: cards.json (HEAD version); env: ID (card id), BSKY_DID, OUT (path).
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

card = next(c for c in json.load(sys.stdin)["cards"]
            if c["id"] == os.environ["ID"])
url = f"https://ctsignal.org/story/{card['id']}"
text = (f"{card['answer_text']}\n\n{url}\n"
        "Know where you live — sources on the page.")
if len(text) > 300:
    text = text[:297] + "..."
rec = {
    "repo": os.environ["BSKY_DID"],
    "collection": "app.bsky.feed.post",
    "record": {
        "text": text,
        "createdAt": datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "embed": {"$type": "app.bsky.embed.external", "external": {
            "uri": url, "title": card["question"],
            "description": card["answer_text"][:200]}},
    },
}
json.dump(rec, open(os.environ.get("OUT", "/tmp/bsky_rec.json"), "w"))
